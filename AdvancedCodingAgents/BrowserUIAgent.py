import asyncio
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from playwright.async_api import async_playwright, Page, Locator


DEMO_DIR = Path("demo_pages")
SCREENSHOT_DIR = Path("screenshots")


NORMAL_HTML = """
<!DOCTYPE html>
<html>
<body>
  <h1>Contact Form</h1>

  <form>
    <label>Name</label>
    <input id="name" name="name" placeholder="Your name">

    <label>Email</label>
    <input id="email" name="email" placeholder="Your email">

    <label>Message</label>
    <textarea id="message" name="message" placeholder="Your message"></textarea>

    <button id="submit-btn" type="button" onclick="document.getElementById('result').innerText='Form submitted successfully'">
      Submit
    </button>
  </form>

  <p id="result"></p>
</body>
</html>
"""


LAYOUT_CHANGED_HTML = """
<!DOCTYPE html>
<html>
<body>
  <h1>Contact Us</h1>

  <form>
    <input data-testid="full-name-input" name="full_name" placeholder="Full name">
    <input data-testid="email-input" name="user_email" placeholder="Email address">
    <textarea data-testid="message-input" name="user_message" placeholder="Write message"></textarea>

    <button data-testid="send-button" type="button" onclick="document.getElementById('result').innerText='Form submitted successfully'">
      Send Message
    </button>
  </form>

  <p id="result"></p>
</body>
</html>
"""


CAPTCHA_HTML = """
<!DOCTYPE html>
<html>
<body>
  <h1>Contact Form</h1>

  <form>
    <input id="name" name="name" placeholder="Your name">
    <input id="email" name="email" placeholder="Your email">
    <textarea id="message" name="message" placeholder="Your message"></textarea>

    <div class="captcha-box">
      <label>CAPTCHA</label>
      <input id="captcha" name="captcha" placeholder="Enter CAPTCHA">
    </div>

    <button id="submit-btn" type="button">Submit</button>
  </form>

  <p id="result"></p>
</body>
</html>
"""


FIELD_SELECTORS: Dict[str, List[str]] = {
    "name": [
        "#name",
        "input[name='name']",
        "input[name='full_name']",
        "[data-testid='full-name-input']",
        "input[placeholder*='name' i]",
    ],
    "email": [
        "#email",
        "input[name='email']",
        "input[name='user_email']",
        "[data-testid='email-input']",
        "input[placeholder*='email' i]",
    ],
    "message": [
        "#message",
        "textarea[name='message']",
        "textarea[name='user_message']",
        "[data-testid='message-input']",
        "textarea[placeholder*='message' i]",
    ],
}


BUTTON_SELECTORS = [
    "#submit-btn",
    "[data-testid='send-button']",
    "button[type='submit']",
    "button",
]


@dataclass
class FormData:
    name: str
    email: str
    message: str


@dataclass
class AgentResult:
    success: bool
    reason: str
    screenshot: Optional[str] = None


def create_demo_pages() -> None:
    DEMO_DIR.mkdir(exist_ok=True)

    (DEMO_DIR / "normal.html").write_text(NORMAL_HTML, encoding="utf-8")
    (DEMO_DIR / "layout_changed.html").write_text(LAYOUT_CHANGED_HTML, encoding="utf-8")
    (DEMO_DIR / "captcha.html").write_text(CAPTCHA_HTML, encoding="utf-8")


class BrowserUIAgent:
    def __init__(self, page: Page):
        self.page = page
        SCREENSHOT_DIR.mkdir(exist_ok=True)

    async def take_screenshot(self, name: str) -> str:
        path = SCREENSHOT_DIR / f"{name}.png"
        await self.page.screenshot(path=str(path), full_page=True)
        return str(path)

    async def detect_captcha(self) -> bool:
        captcha_selectors = [
            "input[name*='captcha' i]",
            "input[id*='captcha' i]",
            ".captcha",
            ".captcha-box",
            "iframe[src*='captcha' i]",
        ]

        for selector in captcha_selectors:
            locator = self.page.locator(selector)

            if await locator.count() > 0:
                return True

        page_text = await self.page.locator("body").inner_text()

        if "captcha" in page_text.lower():
            return True

        return False

    async def find_visible_locator(self, selectors: List[str]) -> Optional[Locator]:
        for selector in selectors:
            locator = self.page.locator(selector)

            count = await locator.count()

            if count == 0:
                continue

            first = locator.first

            try:
                if await first.is_visible():
                    return first
            except Exception:
                continue

        return None

    async def safe_fill(self, field_name: str, value: str) -> bool:
        selectors = FIELD_SELECTORS[field_name]
        locator = await self.find_visible_locator(selectors)

        if locator is None:
            return False

        await locator.fill(value)

        actual_value = await locator.input_value()

        if actual_value != value:
            return False

        return True

    async def safe_click_submit(self) -> bool:
        candidates = []

        for selector in BUTTON_SELECTORS:
            locator = self.page.locator(selector)

            count = await locator.count()

            for i in range(count):
                button = locator.nth(i)

                try:
                    if not await button.is_visible():
                        continue

                    text = (await button.inner_text()).strip().lower()

                    if re.search(r"\b(submit|send|continue)\b", text):
                        candidates.append(button)

                except Exception:
                    continue

        if not candidates:
            return False

        # Wrong-click protection:
        # click only the first visible button whose text matches expected actions.
        button = candidates[0]

        if not await button.is_enabled():
            return False

        await button.click()
        return True

    async def verify_success(self) -> bool:
        result = self.page.locator("#result")

        if await result.count() == 0:
            return False

        text = (await result.inner_text()).lower()

        return "submitted successfully" in text

    async def submit_form(self, url: str, data: FormData) -> AgentResult:
        try:
            await self.page.goto(url)
            await self.page.wait_for_load_state("domcontentloaded")

            if await self.detect_captcha():
                screenshot = await self.take_screenshot("captcha_detected")
                return AgentResult(
                    success=False,
                    reason="CAPTCHA detected. Human approval/manual action required.",
                    screenshot=screenshot,
                )

            field_values = {
                "name": data.name,
                "email": data.email,
                "message": data.message,
            }

            for field_name, value in field_values.items():
                ok = await self.safe_fill(field_name, value)

                if not ok:
                    screenshot = await self.take_screenshot(f"missing_field_{field_name}")
                    return AgentResult(
                        success=False,
                        reason=f"Could not safely fill field: {field_name}",
                        screenshot=screenshot,
                    )

            clicked = await self.safe_click_submit()

            if not clicked:
                screenshot = await self.take_screenshot("submit_button_not_found")
                return AgentResult(
                    success=False,
                    reason="Could not safely identify submit button.",
                    screenshot=screenshot,
                )

            success = await self.verify_success()

            if not success:
                screenshot = await self.take_screenshot("submission_not_verified")
                return AgentResult(
                    success=False,
                    reason="Clicked submit, but success could not be verified.",
                    screenshot=screenshot,
                )

            return AgentResult(
                success=True,
                reason="Form submitted and verified successfully.",
            )

        except Exception as e:
            screenshot = await self.take_screenshot("unexpected_error")
            return AgentResult(
                success=False,
                reason=f"Unexpected browser automation error: {e}",
                screenshot=screenshot,
            )


async def run_demo() -> None:
    create_demo_pages()

    form_data = FormData(
        name="Jenny",
        email="jenny@example.com",
        message="Hello from browser automation agent.",
    )

    test_pages = [
        "normal.html",
        "layout_changed.html",
        "captcha.html",
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        for page_name in test_pages:
            print("\n====================")
            print("Testing page:", page_name)

            page = await browser.new_page()
            agent = BrowserUIAgent(page)

            file_path = (DEMO_DIR / page_name).resolve()
            url = f"file://{file_path}"

            result = await agent.submit_form(url, form_data)

            print("Success:", result.success)
            print("Reason:", result.reason)

            if result.screenshot:
                print("Screenshot:", result.screenshot)

            await page.close()

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run_demo())