# Полоска heartbeat (SYS [...])

class Heartbeat:
    def __init__(self, hb_len, step, start_pos=0):
        self.hb_len = hb_len
        self.step = step
        self.pos = start_pos

    def tick(self):
        """
        Возвращает строку полоски и двигает позицию.
        Логика 1-в-1: '==' за хвостом и '>' голова.
        """
        bar = [" "] * self.hb_len

        if self.pos >= 2:
            bar[self.pos - 2] = "="
        if self.pos >= 1:
            bar[self.pos - 1] = "="
        bar[self.pos] = ">"

        self.pos = (self.pos + self.step) % self.hb_len
        return "".join(bar)
