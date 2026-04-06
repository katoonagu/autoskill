from __future__ import annotations

import asyncio
from dataclasses import dataclass
import random
from typing import Tuple

from playwright.async_api import Locator, Page


def random_between(start: float, end: float) -> float:
    return random.uniform(start, end)


@dataclass
class HumanSettings:
    pause_range_ms: Tuple[int, int] = (120, 320)
    think_range_ms: Tuple[int, int] = (450, 900)
    click_delay_ms: Tuple[int, int] = (70, 160)
    type_delay_ms: Tuple[int, int] = (45, 120)
    move_steps: Tuple[int, int] = (14, 30)
    click_jitter_ratio: float = 0.16
    stability_checks: int = 3
    stability_interval_ms: int = 150


class Humanizer:
    def __init__(self, page: Page, settings: HumanSettings | None = None):
        self.page = page
        self.settings = settings or HumanSettings()

    async def pause(self, min_ms: int | None = None, max_ms: int | None = None) -> None:
        start, end = self.settings.pause_range_ms
        await self.page.wait_for_timeout(random_between(min_ms or start, max_ms or end))

    async def think(self) -> None:
        start, end = self.settings.think_range_ms
        await self.page.wait_for_timeout(random_between(start, end))

    async def safe_scroll_into_view(self, locator: Locator) -> None:
        await locator.scroll_into_view_if_needed()
        await self.pause(60, 160)

    async def wait_for_stable(self, locator: Locator) -> None:
        await locator.wait_for(state="visible")
        await locator.wait_for(state="attached")
        last_box = None
        stable_hits = 0

        while stable_hits < self.settings.stability_checks:
            box = await locator.bounding_box()
            if box is None:
                raise RuntimeError("Locator has no bounding box")

            rounded = tuple(round(box[key], 2) for key in ("x", "y", "width", "height"))
            if rounded == last_box:
                stable_hits += 1
            else:
                stable_hits = 0
            last_box = rounded
            await self.page.wait_for_timeout(self.settings.stability_interval_ms)

    async def _target_point(self, locator: Locator) -> tuple[float, float]:
        box = await locator.bounding_box()
        if box is None:
            raise RuntimeError("Locator has no bounding box")

        jitter_x = box["width"] * self.settings.click_jitter_ratio
        jitter_y = box["height"] * self.settings.click_jitter_ratio
        x = box["x"] + box["width"] / 2 + random_between(-jitter_x, jitter_x)
        y = box["y"] + box["height"] / 2 + random_between(-jitter_y, jitter_y)
        return x, y

    async def human_move_to(self, locator: Locator) -> tuple[float, float]:
        await self.safe_scroll_into_view(locator)
        await self.wait_for_stable(locator)
        x, y = await self._target_point(locator)

        overshoot_x = x + random_between(-12, 12)
        overshoot_y = y + random_between(-10, 10)
        await self.page.mouse.move(
            overshoot_x,
            overshoot_y,
            steps=int(random_between(*self.settings.move_steps)),
        )
        await self.pause(40, 120)
        await self.page.mouse.move(
            x,
            y,
            steps=int(random_between(5, 12)),
        )
        await self.pause(40, 120)
        return x, y

    async def human_click(self, locator: Locator) -> None:
        await locator.wait_for(state="visible")
        x, y = await self.human_move_to(locator)
        await self.pause(40, 160)
        await self.page.mouse.click(
            x,
            y,
            delay=random_between(*self.settings.click_delay_ms),
        )
        await self.pause(120, 280)

    async def human_type(self, locator: Locator, text: str, clear: bool = True) -> None:
        await self.human_click(locator)
        if clear:
            await locator.press("Control+A")
            await self.pause(20, 80)
            await locator.press("Backspace")
            await self.pause(30, 90)
        for char in text:
            await locator.press_sequentially(char, delay=random_between(*self.settings.type_delay_ms))
        await self.pause(100, 220)

    async def human_insert_text(self, locator: Locator, text: str, clear: bool = True) -> None:
        await self.human_click(locator)
        if clear:
            await locator.press("Control+A")
            await self.pause(20, 80)
            await locator.press("Backspace")
            await self.pause(30, 90)
        await self.pause(80, 180)
        await self.page.keyboard.insert_text(text)
        await self.pause(120, 240)

    async def human_wheel_scroll(self, delta_y: int) -> None:
        chunks = max(1, abs(delta_y) // 300)
        step = int(delta_y / chunks)
        for _ in range(chunks):
            await self.page.mouse.wheel(0, step)
            await self.pause(60, 130)
