*This project has been created as part of the 42 curriculum by tsito.*

<h1 align="center">Fly-in</h1>

<p align="center">
  <strong>Space-Time A* route planning for a fleet of autonomous drones</strong>
  <br>
  Move every drone through a capacity-constrained network in as few turns as possible.
</p>

<p align="center">
  <img alt="42 cursus" src="https://img.shields.io/badge/42-cursus-000000?logo=42&logoColor=white">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
  <img alt="uv" src="https://img.shields.io/badge/package_manager-uv-DE5FE9?logo=uv&logoColor=white">
  <img alt="mypy strict" src="https://img.shields.io/badge/mypy-strict-2A6DB2">
  <img alt="flake8" src="https://img.shields.io/badge/flake8-passing-4C9A2A">
</p>

<p align="center">
  <a href="#description">Description</a> •
  <a href="#instructions">Instructions</a> •
  <a href="#example">Example</a> •
  <a href="#algorithm-space-time-a">Algorithm</a> •
  <a href="#visualizer">Visualizer</a> •
  <a href="#performance">Performance</a> •
  <a href="#Japanese">Japanese</a>
</p>

## Description

Fly-in reads a map — a graph of zones joined by bidirectional connections —
and moves every drone from the start hub to the goal in as few turns as
possible.

Zones and connections hold only a limited number of drones at a time, so a
plan cannot stop at *which way* a drone goes. It must also decide *when* the
drone may be there. That is why the planner searches over space **and** time.

The goal is to land every drone on the end hub in the fewest simulation turns,
handling distribution across multiple paths, strategic waiting, and deadlock
avoidance. The graph logic is written from scratch — no `networkx`, `graphlib`
or similar — in fully object-oriented, `mypy --strict` clean Python.

## Instructions

Requirements: Python 3.10+ and [uv](https://docs.astral.sh/uv/).

~~~sh
make install                                     # install dependencies
make run                                         # run the default easy map
make run MAP=maps/hard/01_maze_nightmare.txt     # run any map
~~~

`make run` is a shortcut for:

~~~sh
uv run fly-in maps/hard/01_maze_nightmare.txt
~~~

Add `-g` / `--gui` to open the visualizer window alongside the terminal
output:

~~~sh
uv run fly-in maps/hard/01_maze_nightmare.txt --gui
~~~

Development commands:

~~~sh
make test         # run the pytest suite
make lint         # flake8 and mypy
make lint-strict  # flake8 and mypy --strict
make debug        # run under Python's debugger
make clean        # remove Python caches
~~~

## Map format

A map begins with the drone count. Every zone must be defined before the
connections that reference it. Metadata is optional and goes in square
brackets. Lines starting with `#` are comments, and zone names cannot contain
spaces or dashes.

~~~text
# maps/easy/01_linear_path.txt
nb_drones: 2

start_hub: start 0 0 [color=green]
hub: waypoint1 1 0 [color=blue]
hub: waypoint2 2 0 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-waypoint1
connection: waypoint1-waypoint2
connection: waypoint2-goal
~~~

| Target | Metadata | Default |
| --- | --- | --- |
| Zone | `zone=normal｜priority｜restricted｜blocked` | `normal` |
| Zone | `color=<single-word color>` | none |
| Hub | `max_drones=<positive integer>` | `1` |
| Connection | `max_link_capacity=<positive integer>` | `1` |

| Zone type | Entry cost | Behavior |
| --- | ---: | --- |
| `normal` | 1 turn | Ordinary zone |
| `priority` | 1 turn | Preferred when two candidates tie |
| `restricted` | 2 turns | One turn in transit, then arrival |
| `blocked` | — | Never entered |

## Example

Running the two-drone map above:

~~~sh
uv run fly-in maps/easy/01_linear_path.txt
~~~

Each output line is one simulation turn, listing only the drones that moved.
Waiting and delivered drones are left out, and a drone crossing into a
`restricted` zone shows both ends of its connection:

~~~text
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
~~~

Both drones reach the goal in 4 turns.

## Algorithm: Space-Time A*

Plain A* answers "which zone comes next?". That is not enough here: a zone
that is full on turn 3 may be free on turn 4, so the same zone can be both a
dead end and a good move depending on the timing.

`Space-Time A*` solves this by putting the clock inside the search state.
A node is not a zone but a zone *at a given turn*:

~~~python
@dataclass(frozen=True)
class _SearchState:
    turn: int
    zone_name: str
~~~

From there the search is ordinary A*, with three pieces:

**1. Cost function**

Candidates are ranked by the usual `f = g + h`, where `g` is the turn already
reached and `h` is the estimated turns still to go:

~~~text
f(state) = state.turn + min_turns_to_goal[state.zone_name]
~~~

`min_turns_to_goal` comes from a single backward Dijkstra run from the goal,
done once before any drone is planned and reused by all of them. It ignores
capacity, so it never overestimates — which is what keeps A* optimal. Ties
are broken in favor of `priority` zones.

**2. Neighbors**

Each state expands into a move to every adjacent zone, plus a one-turn wait in
place. Waiting is a real option: it is often faster to let a busy corridor
clear than to detour around it. A move is dropped when the destination is
`blocked`, or when the zone or the connection is already fully booked for the
turns involved.

**3. Cooperative reservations**

Drones are planned one at a time. Once a route is found, the turns it occupies
are recorded in `RouteSchedule`:

~~~python
ZoneSlot       = tuple[int, str]        # (turn, zone)          -> drones inside
ConnectionSlot = tuple[int, str, str]   # (turn, zone_a, zone_b) -> drones crossing
~~~

Connection endpoints are sorted before use as a key, so both directions of
travel draw on the same capacity. The next drone sees those bookings as walls
and routes — or waits — around them.

Entering a `restricted` zone takes two turns, spent on the connection itself:

~~~text
turn 0: start
turn 1: Transit(start, restricted)   # in flight, holding the connection
turn 2: restricted
~~~

~~~mermaid
flowchart TD
    A[Load and validate the map] --> B[Precompute min turns to goal]
    B --> C{Any drone left to plan?}
    C -- Yes --> D["Start from (start zone, turn 0)"]
    D --> E["Pop the candidate with the lowest f"]
    E --> F{At the goal?}
    F -- No --> G["Expand: moves and one-turn wait"]
    G --> H{Zone and connection free on those turns?}
    H -- No --> E
    H -- Yes --> I[Queue the new space-time state]
    I --> E
    F -- Yes --> J[Rebuild the route with Transit states]
    J --> K[Reserve its zones and connections]
    K --> C
    C -- No --> L[Render the schedule]
~~~

## Visualizer

The terminal output stays plain text, because the subject fixes its format
exactly. The visual feedback therefore lives in the GUI: `--gui` opens a Flet
window replaying the same schedule.

Turn-by-turn text answers *what* happened; the window answers *why*. Watching
the drones move makes the plan legible at a glance — where the fleet splits
across parallel paths, which corridor is the bottleneck everyone queues for,
and why a drone chose to wait rather than detour. Zones keep the coordinates
from the map file, rescaled to fit the canvas without distorting the aspect
ratio, so a map keeps the shape its author drew. The window can be resized
freely and the map refits itself.

Every rule of the map format has its own visual channel, so the constraints
the planner obeys can be checked against the picture:

| Channel | Meaning |
| --- | --- |
| Fill color | `color=` metadata, otherwise the zone type |
| Rainbow gradient | `color=rainbow`, swept around the zone center |
| Outline color | Zone type |
| Dashed outline | `restricted` or `blocked` |
| Circle size | Start and end hubs are drawn larger |
| `START` / `GOAL` badge | Start and end hubs |
| Line width | `max_link_capacity` of a connection |
| White dot | One drone, animated between turns |
| Numbered dot | Seven or more drones stacked on one spot |

Zone names are never drawn on the map, so no label can cover another one.
Hovering shows the details instead: a zone reports its name, role, type,
capacity, position and color; a connection reports the two zones it joins and
its capacity; a drone reports its identifier.

Two to six drones sharing a spot sit on the corners of a regular polygon
around its center. From seven, they stack behind a single dot carrying the
count, so a crowded start hub never spills over its neighbours. A drone in
transit sits at the midpoint of its connection.

| Control | Action |
| --- | --- |
| `→` / `←` | One turn forward or back |
| `Space` | Play or pause |
| `Home` | Back to the first turn |
| Speed button | Cycle 1x, 2x, 4x, 0.5x |
| Slider | Jump to any turn |

Playback, the slider and the single-step keys make even a 43-turn schedule
reviewable: pause on the turn that looks wrong, step back one turn, and read
the tooltips of the zones involved.

### Why Flet rather than tkinter

**Animation**

A marker declares `ft.Animation` once and is then simply given a new position;
the framework interpolates the frames. In tkinter the same effect means a
hand-written `after()` loop redrawing every drone on every frame.

**Ready-made widgets**

The slider, the speed button and a layout that refits itself on resize come
with the toolkit, instead of being built and repositioned by hand.

tkinter's advantage is needing no dependency at all, but `make install`
already covers that.

## Performance

The subject scores route quality by simulation turns, not CPU time. Every
provided map meets or beats its target, and the optional challenger
reference is beaten by two turns.

| Map | Drones | Turns | Target | Margin |
| --- | ---: | ---: | ---: | ---: |
| Easy — Linear path | 2 | 4 | ≤ 6 | 2 |
| Easy — Simple fork | 4 | 4 | ≤ 8 | 4 |
| Easy — Basic capacity | 4 | 4 | ≤ 6 | 2 |
| Medium — Dead end trap | 5 | 8 | ≤ 12 | 4 |
| Medium — Circular loop | 6 | 15 | ≤ 15 | 0 |
| Medium — Priority puzzle | 5 | 7 | ≤ 12 | 5 |
| Hard — Maze nightmare | 8 | 13 | ≤ 30 | 17 |
| Hard — Capacity hell | 12 | 16 | ≤ 35 | 19 |
| Hard — Ultimate challenge | 15 | 26 | ≤ 45 | 19 |
| Challenger — The Impossible Dream | 25 | **43** | Reference: 45 | **2** |

## Project structure

~~~text
src/fly_in/
├── main.py           # CLI entry point
├── parsing/          # map file -> Map
├── models/           # Map, Zone, Connection
├── routing/
│   ├── route_planner.py    # Space-Time A*
│   └── route_schedule.py   # routes and capacity reservations
└── rendering/
    ├── terminal.py   # the required per-turn output
    └── gui/          # Flet visualizer (board/ draws the map)
~~~

286 tests cover map parsing and its error cases, blocked / restricted /
priority routing, capacity reservations, strategic waiting, terminal output,
and the visualizer's per-turn state, layout and controls. All sources pass
`flake8` and `mypy --strict`.

## Resources

- [argparse](https://docs.python.org/3/library/argparse.html),
  [heapq](https://docs.python.org/3/library/heapq.html),
  [dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/)
- [A* — Wikipedia](https://en.wikipedia.org/wiki/A*_search_algorithm)
- [Cooperative Pathfinding — David Silver](https://cw.fel.cvut.cz/b211/_media/courses/b3m33mkr/coop-path-aiwisdom.pdf)

### AI usage

AI was used throughout the project, on these tasks and these parts:

| Part | How AI was used |
| --- | --- |
| Reading the subject | Clarifying the requirements and the scoring rules |
| `routing/` | Discussing the space-time search and the reservation strategy, then reviewing the implementation |
| `parsing/`, `models/` | Proposing malformed inputs and edge cases the parser must reject |
| `rendering/gui/` | Reviewing and refactoring the Flet visualizer for readability |
| `tests/` | Generating test cases from the edge cases discussed above |
| `Makefile`, docstrings, `README.md` | Generating the content |

Everything generated was checked against the subject with the test suite,
`flake8`, `mypy --strict` and the provided maps. The disclosure is explicit so
the work can be reviewed transparently; the author remains responsible for
understanding, explaining and maintaining all submitted code.

---

## Japanese

<details>
<summary><strong>open</strong></summary>

## Description

Fly-inは経路計画のシミュレーターである。ゾーンと双方向の接続でできたマップを
読み込み、すべてのドローンをstartからgoalまで最小のターン数で運ぶ。

ゾーンにも接続にも、同時に入れる機数の上限がある。そのため「どの道を通るか」を
決めるだけでは足りず、「いつそこを通るか」まで決めなければならない。探索する
空間に時間の軸が加わるのはこのためである。

目指すのは全機の到着をできるだけ早く終わらせることで、経路の分散、あえての待機、
デッドロックの回避がその手段になる。グラフ処理は`networkx`や`graphlib`に頼らず
自分で実装し、全体をオブジェクト指向で組み、`mypy --strict`を通している。

## Instructions

必要なものはPython 3.10以降と[uv](https://docs.astral.sh/uv/)。

~~~sh
make install                                     # 依存パッケージを入れる
make run                                         # 既定のeasyマップを実行する
make run MAP=maps/hard/01_maze_nightmare.txt     # マップを指定して実行する
~~~

`make run`は次のコマンドの短縮形である。

~~~sh
uv run fly-in maps/hard/01_maze_nightmare.txt
~~~

`-g` / `--gui`を付けると、ターミナル出力に加えて可視化ウィンドウが開く。

~~~sh
uv run fly-in maps/hard/01_maze_nightmare.txt --gui
~~~

開発用のコマンド:

~~~sh
make test         # pytestを実行する
make lint         # flake8とmypyを実行する
make lint-strict  # flake8とmypy --strictを実行する
make debug        # デバッガ付きで実行する
make clean        # Pythonのキャッシュを削除する
~~~

## Map format

マップの1行目はドローンの数。ゾーンは、それを使う接続よりも前に定義しておく。
メタデータは角括弧の中に書き、省略してもよい。`#`から始まる行はコメント。
ゾーン名に空白とハイフンは使えない。

~~~text
# maps/easy/01_linear_path.txt
nb_drones: 2

start_hub: start 0 0 [color=green]
hub: waypoint1 1 0 [color=blue]
hub: waypoint2 2 0 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-waypoint1
connection: waypoint1-waypoint2
connection: waypoint2-goal
~~~

| 対象 | メタデータ | 既定値 |
| --- | --- | --- |
| ゾーン | `zone=normal｜priority｜restricted｜blocked` | `normal` |
| ゾーン | `color=<1語の色名>` | なし |
| ハブ | `max_drones=<正の整数>` | `1` |
| 接続 | `max_link_capacity=<正の整数>` | `1` |

| ゾーンの種類 | 進入コスト | 動作 |
| --- | ---: | --- |
| `normal` | 1ターン | 通常のゾーン |
| `priority` | 1ターン | 候補が同点のときに優先される |
| `restricted` | 2ターン | 1ターン移動してから到着する |
| `blocked` | — | 進入できない |

## Example

上のマップを実行する。

~~~sh
uv run fly-in maps/easy/01_linear_path.txt
~~~

出力は1行が1ターンにあたり、そのターンに動いた機だけを並べる。待機中の機と
到着済みの機は現れない。`restricted`ゾーンへ向かっている途中の機は、接続の
両端をハイフンでつないで表す。

~~~text
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
~~~

2機とも4ターンでgoalに着く。

## Algorithm: Space-Time A*

通常のA*が決めるのは「次にどのゾーンへ進むか」だけだが、この問題ではそれでは
足りない。3ターン目には満員のゾーンが、4ターン目には空いていることがある。
同じゾーンが、通るタイミング次第で行き止まりにも最短手にもなるのだ。

`Space-Time A\*`は、探索の状態そのものに時刻を持たせてこれを解く。ノードは
ゾーンではなく「何ターン目のどのゾーンか」になる。

~~~python
@dataclass(frozen=True)
class _SearchState:
    turn: int
    zone_name: str
~~~

あとは通常のA*と変わらない。要点は3つある。

**1. コスト関数**

候補の順位は`f = g + h`で決める。`g`はそこへ着くまでにかかったターン数、
`h`はgoalまでに残ると見込まれるターン数である。

~~~text
f(state) = state.turn + min_turns_to_goal[state.zone_name]
~~~

`min_turns_to_goal`は、goalから逆向きにダイクストラ法を1回走らせて作る表である。
どの機の計画よりも先に一度だけ計算し、以降は全機で使い回す。収容数の制約を
無視した値なので実際の残りターン数を超えることはなく、A*の最適性は保たれる。
同点の候補があれば`priority`ゾーンを選ぶ。

**2. 候補の展開**

ひとつの状態からは、隣のゾーンへの移動と、その場で1ターン待つ選択肢を作る。
待機も立派な一手で、混んだ通路が空くのを待つほうが遠回りより速いことは
珍しくない。行き先が`blocked`のとき、あるいはそのターンのゾーンや接続が
すでに埋まっているときは、その移動は作らない。

**3. 協調的な予約**

ドローンは1機ずつ順に計画する。経路が決まった機は、自分が占める時刻と場所を
`RouteSchedule`に書き込む。

~~~python
ZoneSlot       = tuple[int, str]        # (ターン, ゾーン)       -> 中にいる機数
ConnectionSlot = tuple[int, str, str]   # (ターン, ゾーンa, ゾーンb) -> 通過する機数
~~~

接続は両端の名前を並べ替えてから鍵にするので、どちら向きに通っても同じ収容数を
消費する。次の機はこの予約を壁として扱い、迂回するか、空くまで待つ。

`restricted`ゾーンに入るには2ターンかかり、そのうち1ターンは接続の上で過ごす。

~~~text
ターン0: start
ターン1: Transit(start, restricted)   # 移動中。接続を占有している
ターン2: restricted
~~~

~~~mermaid
flowchart TD
    A["マップを読み込んで検証する"] --> B["goalまでの最小ターン数を先に求める"]
    B --> C{"まだ計画していない機がいる?"}
    C -- はい --> D["startゾーンのターン0から始める"]
    D --> E["fが最小の候補を取り出す"]
    E --> F{"goalに着いた?"}
    F -- いいえ --> G["移動と1ターンの待機を作る"]
    G --> H{"そのターンにゾーンと接続は空いている?"}
    H -- いいえ --> E
    H -- はい --> I["新しい状態を候補に加える"]
    I --> E
    F -- はい --> J["経路をTransitごと復元する"]
    J --> K["通るゾーンと接続を予約する"]
    K --> C
    C -- いいえ --> L["結果を出力する"]
~~~

## Visualizer

ターミナルの出力は課題が形式を厳密に定めているので、飾りのないテキストのままに
してある。目で見て分かる情報はGUIの役目で、`--gui`を付けるとFletのウィンドウが
開き、同じ計画を再生する。

ターンごとの文字列から分かるのは「何が起きたか」まで。「なぜそうなったか」は
動きを見るのが早い。機体がどこで別々の経路に分かれ、どの通路が全機の待ち行列に
なり、なぜ迂回せずに待つほうを選んだのかが、眺めていれば見えてくる。ゾーンは
マップファイルの座標をそのまま使い、縦横比を保ったまま画面に収めるので、マップは
作者が描いたとおりの形で表示される。ウィンドウは自由に伸縮でき、マップもそれに
追従する。

マップの書式の要素にはひとつずつ見た目を割り当ててあるので、計画が制約を守って
いるかどうかを絵の上で確かめられる。

| 表現 | 意味 |
| --- | --- |
| 塗りの色 | `color=`の指定。無ければゾーンの種類の色 |
| 虹色のグラデーション | `color=rainbow`。色が円周を一周する |
| 輪郭の色 | ゾーンの種類 |
| 破線の輪郭 | `restricted`または`blocked` |
| 円の大きさ | startとgoalは大きく描く |
| `START` / `GOAL`の文字 | startとgoal |
| 線の太さ | 接続の`max_link_capacity` |
| 白い点 | ドローン1機。ターン間を移動する |
| 数字入りの点 | 同じ場所に7機以上が重なっている |

ゾーン名は描いていない。文字同士が重なって読めなくなるからで、代わりにマウスを
乗せると情報が出る。ゾーンなら名前、役割、種類、収容数、座標、色。接続なら
結んでいるゾーンと収容数。ドローンなら識別番号。

同じ場所に2〜6機が居合わせたときは、中心のまわりに正多角形の頂点として並べる。
7機以上になると1つの点にまとめ、機数を数字で書く。混み合ったstartが隣のゾーンまで
はみ出さないようにするためである。移動中の機は接続の中点に置く。

| 操作 | 動作 |
| --- | --- |
| `→` / `←` | 1ターン進む／戻る |
| `Space` | 再生と一時停止 |
| `Home` | 最初のターンに戻る |
| 速度ボタン | 1x、2x、4x、0.5xを順に切り替える |
| スライダー | 任意のターンへ移動する |

再生と一時停止、スライダー、1ターンずつの移動があるので、43ターンの計画でも
無理なく追える。おかしいと思ったターンで止め、1つ戻し、関係するゾーンの
ツールチップを読めばよい。

### Why Flet rather than tkinter

**アニメーション**

マーカーに`ft.Animation`を一度宣言しておけば、あとは新しい座標を渡すだけで、
間のフレームはフレームワークが補間してくれる。tkinterで同じことをするなら、
`after()`のループを自分で回して毎フレーム全機を描き直すことになる。

**出来合いのUI部品**

スライダー、速度ボタン、ウィンドウの伸縮に追従するレイアウトが最初から
揃っている。tkinterでは自分で組み立て、位置を計算し直す必要がある。

tkinterの利点は依存を1つも増やさずに済むことだが、そこは`make install`が
引き受けている。

## Performance

課題が経路の質を測る物差しは、計算時間ではなくシミュレーションのターン数である。
提供されたマップはすべて目標以内に収まり、任意課題のchallengerも参考記録を
2ターン縮めている。

| マップ | 機数 | 結果 | 目標 | 差 |
| --- | ---: | ---: | ---: | ---: |
| Easy — Linear path | 2 | 4 | 6以下 | 2 |
| Easy — Simple fork | 4 | 4 | 8以下 | 4 |
| Easy — Basic capacity | 4 | 4 | 6以下 | 2 |
| Medium — Dead end trap | 5 | 8 | 12以下 | 4 |
| Medium — Circular loop | 6 | 15 | 15以下 | 0 |
| Medium — Priority puzzle | 5 | 7 | 12以下 | 5 |
| Hard — Maze nightmare | 8 | 13 | 30以下 | 17 |
| Hard — Capacity hell | 12 | 16 | 35以下 | 19 |
| Hard — Ultimate challenge | 15 | 26 | 45以下 | 19 |
| Challenger — The Impossible Dream | 25 | **43** | 参考記録45 | **2** |

## Project structure

~~~text
src/fly_in/
├── main.py           # CLIの入り口
├── parsing/          # マップファイル -> Map
├── models/           # Map、Zone、Connection
├── routing/
│   ├── route_planner.py    # Space-Time A*
│   └── route_schedule.py   # 経路と収容数の予約
└── rendering/
    ├── terminal.py   # 課題が求めるターンごとの出力
    └── gui/          # Fletの可視化（board/がマップを描く）
~~~

テストは286件。マップの解析と不正な入力、blocked・restricted・priorityを含む
経路探索、収容数の予約、あえての待機、ターミナル出力、そして可視化のターン
ごとの状態・配置・操作を確認している。すべてのソースが`flake8`と
`mypy --strict`を通る。

## Resources

- [argparse](https://docs.python.org/ja/3/library/argparse.html)、
  [heapq](https://docs.python.org/ja/3/library/heapq.html)、
  [dataclasses](https://docs.python.org/ja/3/library/dataclasses.html)
- [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/)
- [A* - Wikipedia](https://ja.wikipedia.org/wiki/A*)
- [Cooperative Pathfinding — David Silver](https://cw.fel.cvut.cz/b211/_media/courses/b3m33mkr/coop-path-aiwisdom.pdf)

### AI usage

AIは次の部分で利用した。

| 部分 | 利用のしかた |
| --- | --- |
| 課題文の読解 | 要件と採点基準の確認 |
| `routing/` | 空間と時間を合わせた探索と予約方式の検討、および実装のレビュー |
| `parsing/`、`models/` | パーサーが弾くべき不正な入力と境界条件の洗い出し |
| `rendering/gui/` | Fletの可視化のレビューと、読みやすさのためのリファクタリング |
| `tests/` | 上で洗い出した境界条件をもとにしたテストの生成 |
| `Makefile`、docstring、`README.md` | 内容の生成 |

生成した内容はすべて、課題文、テスト、`flake8`、`mypy --strict`、提供された
マップに照らして確認している。レビューが透明になるよう利用箇所を明示するが、
提出したコードを理解し、説明し、保守する責任は作者にある。

</details>
