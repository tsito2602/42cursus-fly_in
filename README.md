*This project has been created as part of the 42 curriculum by tsito.*

<h1 align="center">Fly-in</h1>

<p align="center">
  <strong>Space-time route planning for a fleet of autonomous drones</strong>
  <br>
  Move every drone through a constrained network in as few turns as possible.
</p>

<p align="center">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
  <img alt="uv" src="https://img.shields.io/badge/package_manager-uv-DE5FE9?logo=uv&logoColor=white">
  <img alt="mypy strict" src="https://img.shields.io/badge/mypy-strict-2A6DB2">
  <img alt="flake8" src="https://img.shields.io/badge/flake8-passing-4C9A2A">
  <img alt="pytest" src="https://img.shields.io/badge/pytest-47_passed-0A9EDC?logo=pytest&logoColor=white">
</p>

<p align="center">
  <a href="#instructions">Instructions</a> •
  <a href="#algorithm-and-implementation">Algorithm</a> •
  <a href="#visual-representation">Visualizer</a> •
  <a href="#performance">Performance</a> •
  <a href="#日本語訳">日本語訳</a>
</p>

## Description

Fly-in is a multi-drone routing simulator. It parses a graph of zones and
bidirectional connections, then schedules every drone from the start zone to
the goal while respecting movement costs and capacity constraints.

The planner must solve two problems at the same time:

1. Find a short route through the graph.
2. Decide **when** each drone may use every zone and connection.

That temporal component turns an ordinary graph search into a space-time
search. A location is not only a zone; it is a zone occupied at a particular
simulation turn.

| Zone type | Entry cost | Behavior |
| --- | ---: | --- |
| Normal | 1 turn | Standard traversable zone |
| Priority | 1 turn | Preferred when candidate costs are equal |
| Restricted | 2 turns | Drone spends one turn in transit before arrival |
| Blocked | — | Never entered by the planner |

### Highlights

- Space-Time A*-style search over <code>(zone, turn)</code> states
- Precomputed goal-distance estimates reused by every drone
- Strategic waiting when movement is temporarily unavailable
- Zone and connection capacity reservations
- Explicit in-flight <code>Transit</code> states for restricted movement
- Flet visualizer with playback, speed control, and a turn slider
- 43-turn solution for the 45-turn challenger reference
- Fully typed Python with <code>mypy --strict</code>

## Table of contents

- [Description](#description)
- [Instructions](#instructions)
- [Map Format](#map-format)
- [Example](#example)
- [Algorithm and Implementation](#algorithm-and-implementation)
- [Visual Representation](#visual-representation)
- [Architecture](#architecture)
- [Performance](#performance)
- [Testing and Quality](#testing-and-quality)
- [Project Structure](#project-structure)
- [Resources](#resources)
- [日本語版](#日本語版)

## Instructions

### Requirements

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/)

Install all project and development dependencies:

~~~sh
make install
~~~

Run the default easy map:

~~~sh
make run
~~~

Run a specific map:

~~~sh
make run MAP=maps/medium/03_priority_puzzle.txt
~~~

The equivalent direct command is:

~~~sh
uv run fly-in maps/medium/03_priority_puzzle.txt
~~~

Open the graphical visualizer alongside the terminal output:

~~~sh
uv run fly-in maps/medium/03_priority_puzzle.txt --gui
~~~

| Option | Effect |
| --- | --- |
| <code>-g</code>, <code>--gui</code> | Open the network and the drone positions in a window |

### Development commands

~~~sh
make debug        # Run with Python's debugger
make test         # Run the pytest suite
make lint         # Run flake8 and mypy
make lint-strict  # Run flake8 and mypy --strict
make clean        # Remove Python caches
~~~

## Map Format

A map starts with a positive drone count. Zones must be defined before the
connections that reference them. Metadata is optional and appears inside
square brackets.

~~~text
nb_drones: <positive_integer>

start_hub: <name> <x> <y> [metadata]
end_hub: <name> <x> <y> [metadata]
hub: <name> <x> <y> [metadata]

connection: <zone1>-<zone2> [metadata]
~~~

Supported metadata:

| Target | Metadata | Default |
| --- | --- | --- |
| Zone | <code>zone=normal｜priority｜restricted｜blocked</code> | <code>normal</code> |
| Zone | <code>color=&lt;single-word color&gt;</code> | none |
| Hub | <code>max_drones=&lt;positive integer&gt;</code> | <code>1</code> |
| Connection | <code>max_link_capacity=&lt;positive integer&gt;</code> | <code>1</code> |

Comments begin with <code>#</code>. Zone names cannot contain spaces or dashes.

## Example

### Input

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

### Output

Each line is one simulation turn. Only drones that move during that turn are
printed.

~~~text
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
~~~

## Algorithm and Implementation

### 1. Space-time search

The search state combines a physical zone with a simulation turn:

~~~python
@dataclass(frozen=True)
class _SearchState:
    turn: int
    zone_name: str
~~~

This distinction allows the same zone to appear multiple times in the search
at different turns. From each state, the planner generates:

- movement to every valid adjacent zone;
- a one-turn wait in the current zone.

Candidates are ranked by:

~~~text
elapsed turns + estimated turns to the goal
~~~

When two candidates have the same estimate, a priority zone is preferred.
Blocked zones are never generated.

### 2. Reusable goal-distance estimate

Before planning any drone, the planner runs a backward weighted search from the
goal and stores one turn estimate per reachable zone. This table is calculated
once and reused by every drone instead of recomputing a graph distance during
each search.

### 3. Cooperative reservations

Drones are planned one at a time. After finding a route, the planner registers
its occupied resources in <code>RouteSchedule</code>:

~~~python
ZoneSlot = tuple[int, str]
ConnectionSlot = tuple[int, str, str]
~~~

These keys mean:

- <code>(turn, zone_name)</code>: how many drones occupy a zone on one turn;
- <code>(turn, zone_a, zone_b)</code>: how many drones traverse a connection.

Connection endpoints are sorted before creating the key, so both travel
directions consume the same connection capacity.

Later drones treat full reservation slots as unavailable and may choose another
path or wait.

### 4. Restricted movement

Entering a restricted zone costs two turns:

~~~text
Turn 0: start
Turn 1: Transit(start, restricted)
Turn 2: restricted
~~~

The <code>Transit</code> value reserves the connection during flight and lets
the terminal renderer show that the drone has left its origin but has not yet
arrived.

### Planning flow

~~~mermaid
flowchart TD
    A[Load and validate map] --> B[Precompute goal-distance estimates]
    B --> C{Unplanned drone remains?}
    C -- Yes --> D[Start search at start zone and turn 0]
    D --> E[Choose lowest-priority candidate]
    E --> F{Goal reached?}
    F -- No --> G[Generate adjacent moves and waiting]
    G --> H{Zone and connection capacity available?}
    H -- No --> E
    H -- Yes --> I[Add unseen space-time state]
    I --> E
    F -- Yes --> J[Reconstruct route and Transit states]
    J --> K[Reserve zones and connections]
    K --> C
    C -- No --> L[Render terminal output]
~~~

### Design trade-off

The planner optimizes each drone against routes already reserved by earlier
drones. This keeps conflict handling straightforward and performs well on the
provided maps, but it is not a global joint search over every possible fleet
schedule.

The candidate list intentionally favors readable code. Selecting the next
candidate scans the current list, and neighbor discovery scans the map's
connections. Project scoring is based on simulation turns rather than planner
wall-clock time.

## Visual Representation

### Terminal timeline

The terminal renderer prints one line per turn, in the format required by the
subject:

~~~text
D1-fast_junction D3-start-slow_path1
D1-fast_path D2-fast_junction D3-slow_path1
D1-merge_point D2-fast_path D3-slow_path2
~~~

Waiting and delivered drones are omitted from the line. During restricted
movement, both the origin and the destination appear, separated by a dash.

### Graphical visualizer

The <code>--gui</code> option opens a Flet window rendering the same schedule.
Zones keep the position given by the map file, rescaled to fit the canvas
while preserving the aspect ratio.

| Channel | Meaning |
| --- | --- |
| Fill color | <code>color=</code> metadata, or the zone type when absent |
| Rainbow gradient | <code>color=rainbow</code>, swept around the zone center |
| Outline color | Zone type: normal, priority, restricted, blocked |
| Dashed outline | Restricted or blocked zone |
| Circle size | Start and end hubs are drawn larger |
| <code>START</code> / <code>GOAL</code> badge | Start and end hubs |
| Line width | <code>max_link_capacity</code> of a connection |
| White dot | One drone, animated between turns, outlined in the background color so it stays visible on any zone |
| Numbered dot | Seven or more drones stacked on one location |

Zone names are not drawn on the map, so no label can ever cover another one.
Resting the pointer on a zone shows its name, role, type, capacity, position
and color instead. Resting it on a connection line shows the two zones it
joins, in no particular direction, and its capacity, and resting it on a drone
shows its identifier.

Two to six drones sharing a location sit on the corners of a regular polygon
around its center, so the group stays balanced. From seven, they stack on the
center behind a single dot carrying their count, so a crowded start hub never
spills over its neighbours. A drone in transit sits at the midpoint of its
connection.

| Control | Action |
| --- | --- |
| <code>→</code> / <code>←</code> | One turn forward or back |
| <code>Space</code> | Start or pause the playback |
| <code>Home</code> | Return to the first turn |
| Speed button | Cycle 1x, 2x, 4x, 0.5x |
| Slider | Jump to any turn |

The window can be resized freely; the map refits itself to the new size.

## Architecture

~~~mermaid
flowchart LR
    CLI[CLI / main.py]

    subgraph Parsing
        Parser[MapParser]
        Builder[MapBuilder]
    end

    subgraph Models
        MapModel[Map]
        Zone[Zone]
        Connection[Connection]
    end

    subgraph Routing
        Planner[RoutePlanner]
        Schedule[RouteSchedule]
        Transit[Transit]
    end

    subgraph Rendering
        Terminal[terminal.py]
    end

    CLI --> Parser
    Parser --> Builder
    Builder --> MapModel
    MapModel --> Zone
    MapModel --> Connection
    MapModel --> Planner
    Planner --> Schedule
    Planner --> Transit
    Schedule --> Terminal
    MapModel --> Terminal
    Terminal --> Output[Required terminal timeline]
~~~

The parser, domain models, routing, reservations, and presentation remain
separate.

## Performance

The subject scores route quality by total simulation turns, not by CPU time.
The current implementation meets every provided target and beats the optional
challenger reference.

| Map | Result | Subject target | Margin |
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

## Testing and Quality

~~~sh
make test
make lint
make lint-strict
~~~

The test suite currently contains 285 tests covering:

- valid maps, comments, metadata, and defaults;
- malformed lines, duplicate definitions, and invalid references;
- blocked, restricted, and priority routing;
- zone and connection reservations;
- strategic waiting and unavailable paths;
- terminal output and Transit formatting;
- the per-turn simulation state feeding the visualizer;
- the coordinate transform, the drone layout, and the window controls.

All source files pass <code>flake8</code> and
<code>mypy --strict</code>.

## Project Structure

~~~text
.
├── src/fly_in/
│   ├── main.py
│   ├── models/
│   ├── parsing/
│   ├── rendering/
│   │   ├── terminal.py
│   │   └── gui/
│   └── routing/
│       ├── route_planner.py
│       └── route_schedule.py
├── tests/
├── Makefile
└── pyproject.toml
~~~

## Resources

### References

- [Python argparse documentation](https://docs.python.org/3/library/argparse.html)
- [Python heapq documentation](https://docs.python.org/3/library/heapq.html)
- [Python dataclasses documentation](https://docs.python.org/3/library/dataclasses.html)
- [Python typing documentation](https://docs.python.org/3/library/typing.html)
- [Pydantic documentation](https://docs.pydantic.dev/)
- [A* search algorithm](https://en.wikipedia.org/wiki/A*_search_algorithm)
- [Cooperative Pathfinding — David Silver](https://cw.fel.cvut.cz/b211/_media/courses/b3m33mkr/coop-path-aiwisdom.pdf)

### AI usage

AI was used to clarify assignment requirements, discuss route-planning and
scheduling trade-offs, review implementation details, propose edge cases, and
generate tests, Makefile content, docstrings, and documentation.

The generated work was checked against the subject with automated tests,
<code>flake8</code>, <code>mypy --strict</code>, and provided maps. AI use is
disclosed explicitly so the implementation can be reviewed
transparently; the author remains responsible for understanding, explaining,
and maintaining all submitted code.

---

## 日本語訳

<details>
<summary><strong>日本語訳を開く</strong></summary>

## Description

Fly-inは、複数のドローンをstartゾーンからgoalまで移動させる経路計画
シミュレーターである。ゾーンと双方向の接続からなるグラフを読み込み、
移動コストと収容数の制約を守りながら、全ドローンの経路を決める。

計画では、2つの問題を同時に解く必要がある。

1. グラフ上の短い経路を見つける。
2. 各ドローンが、それぞれのゾーンと接続を**いつ**使うかを決める。

この時間の要素があるため、通常のグラフ探索が空間と時間の探索になる。
位置はゾーンだけでは決まらず、「あるターンに占有しているゾーン」で表す。

| ゾーン | 移動コスト | 動作 |
| --- | ---: | --- |
| normal | 1ターン | 通常のゾーン |
| priority | 1ターン | 推定コストが同じ場合に優先 |
| restricted | 2ターン | 1ターン接続上を移動してから到着 |
| blocked | — | 進入不可 |

### 特徴

- <code>(zone, turn)</code>状態に対するSpace-Time A*形式の探索
- 全ドローンで使い回す、goalまでの推定距離の事前計算
- 移動できないときに意図的に待機する
- ゾーンと接続の収容数の予約
- restrictedへの移動を表す<code>Transit</code>状態
- 再生、速度切り替え、ターンスライダーを備えたFletの可視化
- challengerの参考記録45ターンに対して43ターン
- <code>mypy --strict</code>を通る完全な型付け

## Instructions

### 必要なもの

- Python 3.10以降
- [uv](https://docs.astral.sh/uv/)

依存パッケージをインストールする。

~~~sh
make install
~~~

既定のeasyマップを実行する。

~~~sh
make run
~~~

マップを指定して実行する。

~~~sh
make run MAP=maps/medium/03_priority_puzzle.txt
~~~

同じことを直接実行する場合は次のとおり。

~~~sh
uv run fly-in maps/medium/03_priority_puzzle.txt
~~~

ターミナル表示に加えてGUIを開く。

~~~sh
uv run fly-in maps/medium/03_priority_puzzle.txt --gui
~~~

| オプション | 効果 |
| --- | --- |
| <code>-g</code>, <code>--gui</code> | ネットワークとドローンの位置をウィンドウに表示する |

### 開発用コマンド

~~~sh
make debug        # デバッガ付きで実行する
make test         # pytestを実行する
make lint         # flake8とmypyを実行する
make lint-strict  # flake8とmypy --strictを実行する
make clean        # Pythonのキャッシュを削除する
~~~

## Map Format

マップはドローン数から始まる。ゾーンは、それを参照する接続より先に
定義する。メタデータは省略でき、角括弧の中に書く。

~~~text
nb_drones: <正の整数>

start_hub: <名前> <x> <y> [メタデータ]
end_hub: <名前> <x> <y> [メタデータ]
hub: <名前> <x> <y> [メタデータ]

connection: <ゾーン1>-<ゾーン2> [メタデータ]
~~~

使えるメタデータ:

| 対象 | メタデータ | 既定値 |
| --- | --- | --- |
| ゾーン | <code>zone=normal｜priority｜restricted｜blocked</code> | <code>normal</code> |
| ゾーン | <code>color=&lt;1語の色名&gt;</code> | なし |
| ハブ | <code>max_drones=&lt;正の整数&gt;</code> | <code>1</code> |
| 接続 | <code>max_link_capacity=&lt;正の整数&gt;</code> | <code>1</code> |

<code>#</code>から始まる行はコメントである。ゾーン名に空白とハイフンは
使えない。

## Example

### 入力

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

### 出力

1行が1ターンにあたる。そのターンに動いたドローンだけを表示する。

~~~text
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
~~~

## Algorithm and Implementation

### 1. 空間と時間の探索

探索状態は、ゾーンとターンを組み合わせて持つ。

~~~python
@dataclass(frozen=True)
class _SearchState:
    turn: int
    zone_name: str
~~~

こうすると、同じゾーンが別のターンとして探索に何度も現れる。各状態から
次を作る。

- 進入できる隣接ゾーンへの移動
- 現在地での1ターンの待機

候補は次の値で比較する。

~~~text
経過ターン + goalまでの推定ターン数
~~~

推定が同じ場合はpriorityゾーンを優先する。blockedゾーンは候補に作らない。

### 2. 使い回す、goalまでの推定距離

ドローンの計画を始める前に、goalから重み付きの逆向き探索を1回だけ行い、
到達できる各ゾーンまでの推定ターン数を表に持つ。探索のたびに距離を計算し
直さず、全ドローンでこの表を使い回す。

### 3. 協調的な予約

ドローンは1機ずつ計画する。経路が決まると、使う資源を
<code>RouteSchedule</code>へ登録する。

~~~python
ZoneSlot = tuple[int, str]
ConnectionSlot = tuple[int, str, str]
~~~

それぞれの意味は次のとおり。

- <code>(turn, zone_name)</code>: そのターンにゾーンを占有している機数
- <code>(turn, zone_a, zone_b)</code>: そのターンに接続を通る機数

接続の両端は並べ替えてから鍵にするので、どちら向きに進んでも同じ接続の
収容数を消費する。

後続のドローンは、満員の枠を使えないものとして扱い、別の経路を選ぶか
待機する。

### 4. restrictedへの移動

restrictedゾーンへの進入には2ターンかかる。

~~~text
Turn 0: start
Turn 1: Transit(start, restricted)
Turn 2: restricted
~~~

<code>Transit</code>は移動中も接続を予約し、ターミナル表示で「出発した
が、まだ到着していない」ことを示せるようにする。

### 計画の流れ

~~~mermaid
flowchart TD
    A["マップの読み込みと検証"] --> B["goalまでの推定距離を事前計算"]
    B --> C{"未計画のドローンがある?"}
    C -- はい --> D["startゾーンのターン0から探索を開始"]
    D --> E["最も優先度の高い候補を選ぶ"]
    E --> F{"goalに到達した?"}
    F -- いいえ --> G["隣接への移動と待機を作る"]
    G --> H{"ゾーンと接続に空きがある?"}
    H -- いいえ --> E
    H -- はい --> I["未訪問の状態を追加する"]
    I --> E
    F -- はい --> J["経路とTransit状態を復元する"]
    J --> K["ゾーンと接続を予約する"]
    K --> C
    C -- いいえ --> L["ターミナルに出力する"]
~~~

### 設計上の割り切り

各ドローンは、先に計画したドローンの予約を前提に最適化する。衝突の扱いが
分かりやすくなり、提供マップでは十分な結果が出るが、全機の組み合わせを
まとめて探索する方式ではない。

候補の管理も読みやすさを優先している。次の候補を選ぶときは今の候補一覧を
走査し、隣接の探索はマップの接続を走査する。課題の評価は計画にかかる時間
ではなくシミュレーションのターン数なので、この選択で問題ない。

## Visual Representation

### ターミナル

課題が求める形式で、1行に1ターン分の移動を表示する。

~~~text
D1-fast_junction D3-start-slow_path1
D1-fast_path D2-fast_junction D3-slow_path1
D1-merge_point D2-fast_path D3-slow_path2
~~~

待機中と到着済みのドローンは行に出さない。restrictedへの移動中は、
出発したゾーンと到着するゾーンをハイフンでつないで表示する。

### GUI

<code>--gui</code>はFletのウィンドウを開き、同じ結果を再生する。ゾーンは
マップファイルの座標のまま、縦横比を保ってキャンバスに収まるよう
拡大縮小して配置する。

| 表現 | 意味 |
| --- | --- |
| 塗りの色 | <code>color=</code>の指定。無い場合はゾーンの種類の色 |
| 虹色のグラデーション | <code>color=rainbow</code>。色が円周を一周する |
| 輪郭の色 | ゾーンの種類（normal、priority、restricted、blocked） |
| 破線の輪郭 | restrictedまたはblockedのゾーン |
| 円の大きさ | startとgoalは大きく描く |
| <code>START</code> / <code>GOAL</code>の文字 | startとgoal |
| 線の太さ | 接続の<code>max_link_capacity</code> |
| 白い点 | ドローン1機。ターン間を移動し、どのゾーンの上でも見えるよう背景色の輪郭を付ける |
| 数字入りの点 | 同じ場所に7機以上が重なっている |

ゾーン名はマップ上に描かないので、文字同士が重なることがない。代わりに
マウスを乗せると情報が出る。ゾーンでは名前、役割、種類、収容数、座標、色を、
接続の線では結んでいる2つのゾーン（向きは持たない）と収容数を、
ドローンでは識別番号を表示する。

同じ場所にいるドローンが2〜6機のときは、中心のまわりに正多角形の頂点として
並べるので、偏りなく見える。7機以上になると中心に重ね、機数を書いた点を
1つだけ表示するため、混雑したstartが隣のゾーンにはみ出すことはない。
移動中のドローンは、接続の中点に置く。

| 操作 | 動作 |
| --- | --- |
| <code>→</code> / <code>←</code> | 1ターン進む／戻る |
| <code>Space</code> | 再生と一時停止 |
| <code>Home</code> | 最初のターンに戻る |
| 速度ボタン | 1x、2x、4x、0.5xを順に切り替える |
| スライダー | 任意のターンへ移動する |

ウィンドウの大きさは自由に変えられ、マップは新しい大きさに合わせて
描き直される。

## Architecture

~~~mermaid
flowchart LR
    CLI["CLI / main.py"]

    subgraph Parsing["解析"]
        Parser["MapParser"]
        Builder["MapBuilder"]
    end

    subgraph Models["モデル"]
        MapModel["Map"]
        Zone["Zone"]
        Connection["Connection"]
    end

    subgraph Routing["経路計画"]
        Planner["RoutePlanner"]
        Schedule["RouteSchedule"]
        Transit["Transit"]
    end

    subgraph Rendering["表示"]
        Terminal["terminal.py"]
    end

    CLI --> Parser
    Parser --> Builder
    Builder --> MapModel
    MapModel --> Zone
    MapModel --> Connection
    MapModel --> Planner
    Planner --> Schedule
    Planner --> Transit
    Schedule --> Terminal
    MapModel --> Terminal
    Terminal --> Output["課題が求めるターミナル出力"]
~~~

解析、モデル、経路計画、予約、表示はそれぞれ分けている。

## Performance

課題は、計算時間ではなくシミュレーションのターン数で経路の質を評価する。
現在の実装はすべての提供マップで目標を満たし、challengerの参考記録も
上回っている。

| マップ | 結果 | 課題目標 | 差 |
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

## Testing and Quality

~~~sh
make test
make lint
make lint-strict
~~~

285件のテストで、次を確認している。

- 正しいマップ、コメント、メタデータ、既定値
- 不正な行、定義の重複、存在しない参照
- blocked、restricted、priorityを含む経路探索
- ゾーンと接続の予約
- 意図的な待機と、経路が使えない場合の動作
- ターミナル出力と<code>Transit</code>の表示
- GUIに渡すターンごとの状態
- GUIの座標変換、ドローンの配置、ウィンドウの操作

すべてのソースが<code>flake8</code>と<code>mypy --strict</code>を通る。

## Project Structure

~~~text
.
├── src/fly_in/
│   ├── main.py
│   ├── models/
│   ├── parsing/
│   ├── rendering/
│   │   ├── terminal.py
│   │   └── gui/
│   └── routing/
│       ├── route_planner.py
│       └── route_schedule.py
├── tests/
├── Makefile
└── pyproject.toml
~~~

## Resources

### 参考資料

- [Python argparse documentation](https://docs.python.org/3/library/argparse.html)
- [Python heapq documentation](https://docs.python.org/3/library/heapq.html)
- [Python dataclasses documentation](https://docs.python.org/3/library/dataclasses.html)
- [Python typing documentation](https://docs.python.org/3/library/typing.html)
- [Pydantic documentation](https://docs.pydantic.dev/)
- [A* search algorithm](https://en.wikipedia.org/wiki/A*_search_algorithm)
- [Cooperative Pathfinding — David Silver](https://cw.fel.cvut.cz/b211/_media/courses/b3m33mkr/coop-path-aiwisdom.pdf)

### AI usage

AIは、課題要件の確認、経路探索とスケジューリング方針の検討、実装レビュー、
境界値の提案、テスト、Makefile、docstring、READMEの生成に使用した。

生成物は課題文、自動テスト、<code>flake8</code>、
<code>mypy --strict</code>、提供マップで確認した。AI利用を
明示し、提出するすべてのコードについて作者が理解、説明、保守する責任を
持つ。

</details>
