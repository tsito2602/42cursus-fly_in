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
  <a href="#quick-start">Quick start</a> •
  <a href="#map-format">Map format</a> •
  <a href="#algorithm-space-time-a">Algorithm</a> •
  <a href="#visualizer">Visualizer</a> •
  <a href="#performance">Performance</a> •
  <a href="#日本語版">日本語版</a>
</p>

## Overview

Fly-in reads a map — a graph of zones joined by bidirectional connections —
and moves every drone from the start hub to the goal in as few turns as
possible.

Zones and connections hold only a limited number of drones at a time, so a
plan cannot stop at *which way* a drone goes. It must also decide *when* the
drone may be there. That is why the planner searches over space **and** time.

## Quick start

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

The output prints one line per turn, listing only the drones that moved:

~~~text
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
~~~

## Algorithm: Space-Time A*

Plain A* answers "which zone comes next?". That is not enough here: a zone
that is full on turn 3 may be free on turn 4, so the same zone can be both a
dead end and a good move depending on the timing.

**Space-Time A\*** solves this by putting the clock inside the search state.
A node is not a zone but a zone *at a given turn*:

~~~python
@dataclass(frozen=True)
class _SearchState:
    turn: int
    zone_name: str
~~~

From there the search is ordinary A*, with three pieces:

**1. Cost function.** Candidates are ranked by the usual `f = g + h`, where
`g` is the turn already reached and `h` is the estimated turns still to go:

~~~text
f(state) = state.turn + min_turns_to_goal[state.zone_name]
~~~

`min_turns_to_goal` comes from a single backward Dijkstra run from the goal,
done once before any drone is planned and reused by all of them. It ignores
capacity, so it never overestimates — which is what keeps A* optimal. Ties
are broken in favor of `priority` zones.

**2. Neighbors.** Each state expands into a move to every adjacent zone, plus
a one-turn wait in place. Waiting is a real option: it is often faster to let
a busy corridor clear than to detour around it. A move is dropped when the
destination is `blocked`, or when the zone or the connection is already fully
booked for the turns involved.

**3. Cooperative reservations.** Drones are planned one at a time. Once a
route is found, the turns it occupies are recorded in `RouteSchedule`:

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

**Trade-off.** Each drone is optimal given the drones planned before it, but
the fleet as a whole is not searched jointly. This keeps conflict handling
simple and comfortably beats every target on the provided maps. The candidate
list is a plain list scanned linearly rather than a heap, since the subject
scores simulation turns, not planner runtime.

## Visualizer

`--gui` opens a Flet window replaying the same schedule. Zones keep the
coordinates from the map file, rescaled to fit the canvas without distorting
the aspect ratio. The window can be resized freely and the map refits itself.

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

## Performance

The subject scores route quality by simulation turns, not CPU time. Every
provided map beats its target, including the optional challenger reference.

| Map | Result | Target | Margin |
| --- | ---: | ---: | ---: |
| Easy — Linear path | 4 | ≤ 6 | 2 |
| Easy — Simple fork | 4 | ≤ 8 | 4 |
| Easy — Basic capacity | 4 | ≤ 6 | 2 |
| Medium — Dead end trap | 8 | ≤ 12 | 4 |
| Medium — Circular loop | 15 | ≤ 15 | 0 |
| Medium — Priority puzzle | 7 | ≤ 12 | 5 |
| Hard — Maze nightmare | 13 | ≤ 30 | 17 |
| Hard — Capacity hell | 16 | ≤ 35 | 19 |
| Hard — Ultimate challenge | 26 | ≤ 45 | 19 |
| Challenger — The Impossible Dream | **43** | Reference: 45 | **2** |

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

AI was used to clarify the subject, discuss planning and scheduling
trade-offs, review the implementation, propose edge cases, and generate
tests, Makefile content, docstrings and documentation. The results were
checked against the subject with the test suite, `flake8`, `mypy --strict`
and the provided maps. The disclosure is explicit so the work can be reviewed
transparently; the author remains responsible for understanding, explaining
and maintaining all submitted code.

---

## 日本語版

<details>
<summary><strong>日本語版を開く</strong></summary>

## 概要

Fly-inは、ゾーンと双方向の接続からなるマップを読み込み、すべてのドローンを
startからgoalまで最小のターン数で移動させる経路計画シミュレーターである。

ゾーンにも接続にも同時に入れる機数の上限がある。そのため「どの道を通るか」
だけでは計画が決まらず、「いつそこにいてよいか」まで決める必要がある。
だから探索の対象は空間だけでなく、時間も含む。

## 使い方

必要なもの: Python 3.10以降と[uv](https://docs.astral.sh/uv/)。

~~~sh
make install                                     # 依存パッケージを入れる
make run                                         # 既定のeasyマップを実行
make run MAP=maps/hard/01_maze_nightmare.txt     # マップを指定して実行
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

## マップの書式

マップはドローン数から始まる。ゾーンは、それを参照する接続よりも先に
定義する。メタデータは省略でき、角括弧の中に書く。`#`で始まる行はコメント
で、ゾーン名に空白とハイフンは使えない。

~~~text
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

出力は1行が1ターンにあたり、そのターンに動いたドローンだけを並べる。

~~~text
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
~~~

## アルゴリズム: Space-Time A*

普通のA*が答えるのは「次にどのゾーンへ行くか」である。それではここでは
足りない。3ターン目に満員のゾーンも、4ターン目には空いているかもしれない。
つまり同じゾーンが、タイミング次第で行き止まりにも最善手にもなる。

**Space-Time A\***は、探索の状態に時刻を持たせてこれを解く。ノードは
ゾーンではなく、「あるターンのゾーン」である。

~~~python
@dataclass(frozen=True)
class _SearchState:
    turn: int
    zone_name: str
~~~

ここから先は普通のA*で、要点は3つある。

**1. コスト関数。** 候補は`f = g + h`で順位付けする。`g`はすでに到達した
ターン、`h`はgoalまでの残りターン数の見積もりである。

~~~text
f(state) = state.turn + min_turns_to_goal[state.zone_name]
~~~

`min_turns_to_goal`は、goalから逆向きにダイクストラ法を1回だけ走らせて
作る表で、ドローンの計画を始める前に一度計算し、全機で使い回す。収容数の
制約を無視しているので実際より大きい値にはならず、A*の最適性が保たれる。
同点のときは`priority`ゾーンを選ぶ。

**2. 次の候補。** 各状態から、隣接ゾーンへの移動と、その場での1ターンの
待機を作る。待機は立派な選択肢である。混んでいる通路が空くのを待つほうが、
遠回りするより速いことは多い。行き先が`blocked`のとき、またはそのターンの
ゾーンや接続がすでに埋まっているときは、その移動を作らない。

**3. 協調的な予約。** ドローンは1機ずつ計画する。経路が決まると、占有する
ターンを`RouteSchedule`に記録する。

~~~python
ZoneSlot       = tuple[int, str]        # (ターン, ゾーン)       -> 中にいる機数
ConnectionSlot = tuple[int, str, str]   # (ターン, ゾーンa, ゾーンb) -> 通過する機数
~~~

接続の両端は並べ替えてから鍵にするので、どちら向きに進んでも同じ収容数を
消費する。次のドローンはこの予約を壁とみなし、迂回するか待機する。

`restricted`ゾーンへの進入には2ターンかかり、その1ターンは接続の上で
過ごす。

~~~text
ターン0: start
ターン1: Transit(start, restricted)   # 移動中。接続を占有している
ターン2: restricted
~~~

~~~mermaid
flowchart TD
    A["マップを読み込んで検証する"] --> B["goalまでの最小ターン数を事前計算する"]
    B --> C{"未計画のドローンがいる?"}
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

**割り切り。** 各ドローンは、先に計画した機の予約を前提とすれば最適だが、
全機の組み合わせをまとめて探索してはいない。この方式なら衝突の扱いが
単純に保て、提供されたマップではどれも目標を余裕をもって下回る。候補の
管理もヒープではなく素朴なリストの走査にしている。課題が評価するのは
シミュレーションのターン数であって、計画にかかる時間ではないからである。

## 可視化

`--gui`を付けるとFletのウィンドウが開き、同じ結果を再生する。ゾーンは
マップファイルの座標のまま、縦横比を保ってキャンバスに収まるよう拡大縮小
して配置する。ウィンドウの大きさは自由に変えられ、マップは新しい大きさに
合わせて描き直される。

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

ゾーン名はマップ上に描かないので、文字同士が重なることがない。代わりに
マウスを乗せると情報が出る。ゾーンでは名前、役割、種類、収容数、座標、色。
接続では結んでいる2つのゾーンと収容数。ドローンでは識別番号。

同じ場所にいるドローンが2〜6機のときは、中心のまわりに正多角形の頂点として
並べる。7機以上になると中心に重ね、機数を書いた点を1つだけ表示するので、
混雑したstartが隣のゾーンにはみ出すことはない。移動中のドローンは接続の
中点に置く。

| 操作 | 動作 |
| --- | --- |
| `→` / `←` | 1ターン進む／戻る |
| `Space` | 再生と一時停止 |
| `Home` | 最初のターンに戻る |
| 速度ボタン | 1x、2x、4x、0.5xを順に切り替える |
| スライダー | 任意のターンへ移動する |

## 実行結果

課題は、計算時間ではなくシミュレーションのターン数で経路の質を評価する。
提供されたマップはすべて目標を下回り、任意課題のchallengerの参考記録も
上回っている。

| マップ | 結果 | 目標 | 差 |
| --- | ---: | ---: | ---: |
| Easy — Linear path | 4 | 6以下 | 2 |
| Easy — Simple fork | 4 | 8以下 | 4 |
| Easy — Basic capacity | 4 | 6以下 | 2 |
| Medium — Dead end trap | 8 | 12以下 | 4 |
| Medium — Circular loop | 15 | 15以下 | 0 |
| Medium — Priority puzzle | 7 | 12以下 | 5 |
| Hard — Maze nightmare | 13 | 30以下 | 17 |
| Hard — Capacity hell | 16 | 35以下 | 19 |
| Hard — Ultimate challenge | 26 | 45以下 | 19 |
| Challenger — The Impossible Dream | **43** | 参考記録45 | **2** |

## ディレクトリ構成

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

286件のテストで、マップの解析とその異常系、blocked・restricted・priorityを
含む経路探索、収容数の予約、意図的な待機、ターミナル出力、可視化のターン
ごとの状態・配置・操作を確認している。すべてのソースが`flake8`と
`mypy --strict`を通る。

## 参考資料

- [argparse](https://docs.python.org/ja/3/library/argparse.html)、
  [heapq](https://docs.python.org/ja/3/library/heapq.html)、
  [dataclasses](https://docs.python.org/ja/3/library/dataclasses.html)
- [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/)
- [A* - Wikipedia](https://ja.wikipedia.org/wiki/A*)
- [Cooperative Pathfinding — David Silver](https://cw.fel.cvut.cz/b211/_media/courses/b3m33mkr/coop-path-aiwisdom.pdf)

### AIの利用について

AIは、課題要件の確認、経路探索とスケジューリングの方針の検討、実装の
レビュー、境界条件の洗い出し、テスト・Makefile・docstring・ドキュメントの
生成に利用した。生成物は課題文、テスト、`flake8`、`mypy --strict`、提供
マップで確認している。透明にレビューできるよう利用を明示するが、提出した
コードを理解し、説明し、保守する責任は作者にある。

</details>
