import io
import random
import string
from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
from enum import Enum


class CaptchaType(Enum):
    DIGITS = "digits"
    LETTERS = "letters"
    MIXED = "mixed"
    MATH = "math"


class CaptchaGenerator:
    def __init__(self, width: int = 200, height: int = 80):
        self.width = width
        self.height = height
        self.font_size = int(height * 0.7)
        self._load_font()

    def _load_font(self):
        try:
            self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", self.font_size)
        except:
            try:
                self.font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", self.font_size)
            except:
                self.font = ImageFont.load_default()

    def _random_color(self, min_val: int = 0, max_val: int = 200) -> Tuple[int, int, int]:
        return (
            random.randint(min_val, max_val),
            random.randint(min_val, max_val),
            random.randint(min_val, max_val),
        )

    def _add_noise(self, draw: ImageDraw.ImageDraw):
        for _ in range(random.randint(100, 300)):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            draw.point((x, y), fill=self._random_color(50, 150))

    def _add_lines(self, draw: ImageDraw.ImageDraw):
        for _ in range(random.randint(3, 6)):
            x1 = random.randint(0, self.width)
            y1 = random.randint(0, self.height)
            x2 = random.randint(0, self.width)
            y2 = random.randint(0, self.height)
            draw.line([(x1, y1), (x2, y2)], fill=self._random_color(80, 180), width=random.randint(1, 2))

    def _generate_digits(self, length: int = 4) -> Tuple[str, str]:
        code = "".join(random.choices(string.digits, k=length))
        return code, code

    def _generate_letters(self, length: int = 4) -> Tuple[str, str]:
        letters = string.ascii_uppercase
        code = "".join(random.choices(letters, k=length))
        return code, code

    def _generate_mixed(self, length: int = 4) -> Tuple[str, str]:
        chars = string.ascii_uppercase + string.digits
        code = "".join(random.choices(chars, k=length))
        return code, code

    def _generate_math(self) -> Tuple[str, str]:
        ops = ["+", "-", "×"]
        op = random.choice(ops)
        if op == "+":
            a = random.randint(10, 50)
            b = random.randint(10, 50)
            display = f"{a}+{b}=?"
            answer = str(a + b)
        elif op == "-":
            a = random.randint(20, 50)
            b = random.randint(10, a - 1)
            display = f"{a}-{b}=?"
            answer = str(a - b)
        else:
            a = random.randint(2, 12)
            b = random.randint(2, 12)
            display = f"{a}×{b}=?"
            answer = str(a * b)
        return display, answer

    def generate_captcha(self, captcha_type: CaptchaType = CaptchaType.MIXED, length: int = 4) -> Tuple[bytes, str]:
        if captcha_type == CaptchaType.DIGITS:
            display_text, answer = self._generate_digits(length)
        elif captcha_type == CaptchaType.LETTERS:
            display_text, answer = self._generate_letters(length)
        elif captcha_type == CaptchaType.MATH:
            display_text, answer = self._generate_math()
        else:
            display_text, answer = self._generate_mixed(length)

        bg_color = self._random_color(200, 255)
        image = Image.new("RGB", (self.width, self.height), bg_color)
        draw = ImageDraw.Draw(image)

        self._add_lines(draw)
        self._add_noise(draw)

        x_pos = 20
        for char in display_text:
            y_offset = random.randint(-10, 10)
            x_pos += random.randint(5, 15)
            color = self._random_color(20, 120)
            draw.text(
                (x_pos, (self.height - self.font_size) // 2 + y_offset),
                char,
                font=self.font,
                fill=color,
            )
            x_pos += self.font_size // 2

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue(), answer
