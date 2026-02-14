# Метрики SSH

import subprocess

def get_ssh_load():
    try:
        out = subprocess.check_output(
            ["ps", "-C", "ssh", "-o", "%cpu="],
            text=True
        )
        values = [float(x) for x in out.split()]
        return sum(values)
    except Exception:
        return None


def get_sshd_cpu_top_with_count():
    try:
        pids = subprocess.check_output(["pgrep", "ssh"], text=True).split()
        if not pids:
            return 0.0, 0

        pid_list = ",".join(pids)
        out = subprocess.check_output(
            ["top", "-b", "-n", "1", "-p", pid_list],
            text=True,
            stderr=subprocess.DEVNULL
        )

        total = 0.0
        lines = 0
        for line in out.splitlines():
            line = line.strip()
            if not line or not line[0].isdigit():
                continue
            cols = line.split()

            # ?????? %CPU ????? ???? ?? ?? 8 ??????? ??-?? ?????? ?????? top.
            # ????????? ?????????: ?????? ???????, ??????? ?? ????? ? ??????, ????? ? %MEM.
            # ?? ??????? ? ??????????? ???????:
            try:
                total += float(cols[8].replace(",", "."))
                lines += 1
                continue
            except Exception:
                pass

        return total, lines
    except subprocess.CalledProcessError:
        return 0.0, 0
    except Exception:
        return None, 0
