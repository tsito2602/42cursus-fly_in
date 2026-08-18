import flet as ft

from typing import Callable

from .theme import LABEL


class ControlBar(ft.Row):
    """Show the playback buttons, the speed button, and the turn slider."""

    def __init__(
        self,
        last_turn: int,
        on_step: Callable[[int], None],
        on_seek: Callable[[int], None],
        on_toggle: Callable[[], None],
        on_speed: Callable[[], None],
    ) -> None:
        self._last_turn = last_turn
        self._on_step = on_step
        self._on_seek = on_seek
        self._play = ft.IconButton(
            icon=ft.Icons.PLAY_ARROW,
            icon_color=LABEL,
            tooltip="Play",
            on_click=on_toggle,
        )
        self._speed = ft.TextButton(
            content="1x", tooltip="Speed", on_click=on_speed,
            style=ft.ButtonStyle(
                color=LABEL, mouse_cursor=ft.MouseCursor.CLICK
            ),
        )
        self._slider = ft.Slider(
            min=0,
            max=max(1, last_turn),
            divisions=max(1, last_turn),
            value=0,
            expand=True,
            on_change=self._slide,
        )

        super().__init__(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.SKIP_PREVIOUS,
                    tooltip="First turn",
                    icon_color=LABEL,
                    on_click=self._first,
                    mouse_cursor=ft.MouseCursor.CLICK
                ),
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT,
                    tooltip="Previous turn",
                    icon_color=LABEL,
                    on_click=self._previous,
                    mouse_cursor=ft.MouseCursor.CLICK
                ),
                self._play,
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT,
                    tooltip="Next turn",
                    icon_color=LABEL,
                    on_click=self._next,
                    mouse_cursor=ft.MouseCursor.CLICK
                ),
                ft.IconButton(
                    icon=ft.Icons.SKIP_NEXT,
                    tooltip="Last turn",
                    icon_color=LABEL,
                    on_click=self._last,
                    mouse_cursor=ft.MouseCursor.CLICK
                ),
                self._speed,
                self._slider,
            ],
            alignment=ft.MainAxisAlignment.START,
        )

    def set_turn(self, turn: int) -> None:
        """Move the slider to the given turn."""

        self._slider.value = turn
        self._slider.update()

    def set_playing(self, playing: bool) -> None:
        """Show a pause icon while the playback runs."""

        self._play.icon = (
            ft.Icons.PAUSE if playing else ft.Icons.PLAY_ARROW
        )
        self._play.tooltip = "Pause" if playing else "Play"
        self._play.update()

    def set_speed(self, speed: float) -> None:
        """Show the current playback speed."""

        self._speed.content = f"{speed:g}x"
        self._speed.update()

    def _first(self) -> None:
        """Jump to the first turn."""

        self._on_seek(0)

    def _last(self) -> None:
        """Jump to the last turn."""

        self._on_seek(self._last_turn)

    def _previous(self) -> None:
        """Go back one turn."""

        self._on_step(-1)

    def _next(self) -> None:
        """Go forward one turn."""

        self._on_step(1)

    def _slide(self, e: ft.Event[ft.Slider]) -> None:
        """Jump to the turn picked on the slider."""

        self._on_seek(int(e.control.value or 0))
