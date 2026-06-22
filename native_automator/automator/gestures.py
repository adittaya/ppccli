"""Touch gestures: swipe, scroll, pinch, long press."""

import random

class Gestures:
    """Pre-built gesture patterns for common UI actions."""

    @staticmethod
    def swipe_up(x=540, start_y=1600, end_y=300, duration=400):
        return {"x1": x, "y1": start_y, "x2": x, "y2": end_y, "duration": duration}

    @staticmethod
    def swipe_down(x=540, start_y=400, end_y=1600, duration=400):
        return {"x1": x, "y1": start_y, "x2": x, "y2": end_y, "duration": duration}

    @staticmethod
    def swipe_left(y=800, start_x=900, end_x=100, duration=300):
        return {"x1": start_x, "y1": y, "x2": end_x, "y2": y, "duration": duration}

    @staticmethod
    def swipe_right(y=800, start_x=100, end_x=900, duration=300):
        return {"x1": start_x, "y1": y, "x2": end_x, "y2": y, "duration": duration}

    @staticmethod
    def scroll_down(steps=3):
        return {"action": "scroll_down", "steps": steps}

    @staticmethod
    def scroll_up(steps=3):
        return {"action": "scroll_up", "steps": steps}

    @staticmethod
    def long_press(x, y, duration=1000):
        return {"action": "long_press", "x": x, "y": y, "duration": duration}

    @staticmethod
    def pinch_in(center_x=540, center_y=900, distance=200, duration=500):
        return {
            "action": "pinch", "type": "in",
            "x1": center_x - distance, "y1": center_y,
            "x2": center_x + distance, "y2": center_y,
            "cx": center_x, "cy": center_y,
            "duration": duration
        }

    @staticmethod
    def pinch_out(center_x=540, center_y=900, distance=200, duration=500):
        return {
            "action": "pinch", "type": "out",
            "x1": center_x, "y1": center_y,
            "x2": center_x, "y2": center_y,
            "cx": center_x - distance, "cy": center_y,
            "duration": duration
        }

    @staticmethod
    def human_swipe_up(x=None, y1=None, y2=None, wobble=15):
        """Swipe up with slight horizontal wobble to look human."""
        import random
        x = x or random.randint(300, 700)
        y1 = y1 or random.randint(1400, 1700)
        y2 = y2 or random.randint(200, 400)
        return {
            "x1": x + random.randint(-wobble, wobble),
            "y1": y1 + random.randint(-wobble, wobble),
            "x2": x + random.randint(-wobble, wobble),
            "y2": y2 + random.randint(-wobble, wobble),
            "duration": random.randint(300, 600)
        }

    @staticmethod
    def random_tap(region=(100, 200, 900, 1700)):
        """Tap a random point within a region: (x1, y1, x2, y2)."""
        import random
        x = random.randint(region[0], region[2])
        y = random.randint(region[1], region[3])
        return {"x": x, "y": y}
