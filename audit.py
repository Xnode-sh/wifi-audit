import getpass
import math
import re
import string
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
DICT = BASE / "dict-top10000.txt"

import unicodedata


def load_dict():
    try:
        return {line.strip().lower() for line in DICT.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()}
    except FileNotFoundError:
        return set()


COMMON_NAMES = {
    "андрей", "андрюша", "алекс", "александр", "алексей", "антон", "артем", "артём",
    "вова", "виктор", "вадим", "вася", "василий", "владимир", "влад", "дима", "димитрий",
    "дмитрий", "ден", "денис", "егор", "жена", "жора", "иван", "игорь", "илья", "кирилл",
    "костя", "константин", "леха", "лёха", "мак", "максим", "макс", "миха", "миша",
    "михаил", "никита", "олег", "паша", "павел", "петя", "даша", "даник", "данила",
    "ром", "роман", "ростик", "сергей", "серега", "серый", "слава", "ставший",
    "тима", "тимофей", "толя", "федя", "юра", "юрий", "ян",
    "андрейка", "драгун", "жучка", "кот", "котя", "котик", "люба", "люда",
    "ольга", "оля", "оксана", "оksana", "наташа", "наталия", "лена", "катя",
    "катюха", "катюша", "ирина", "галя", "галина", "вика", "виктория", "вероника",
    "алекс", "алиса", "аня", "анка", "богдан", "богдашка", "валера", "вала",
    "вероника", "владик", "владлен", "гена", "генадий", "глеб", "гоша", "гриша",
    "григорий", "джордж", "димасик", "диман", "димон", "евген", "евгений", "женя",
    "захар", "зоя", "инна", "карина", "катя", "клюша", "крис", "кристина", "ксюша",
    "ксения", "кира", "лара", "лариса", "лера", "леша", "лёша", "люся", "марина",
    "мария", "маша", "мила", "милана", "милослава", "митя", "надя", "настя",
    "ната", "нина", "ольга", "павлик", "полина", "рая", "рита", "рустам", "саня",
    "света", "светлана", "сева", "софия", "софья", "стас", "степа", "таня",
    "тамара", "тарас", "тёма", "темка", "уля", "эдик", "эля", "юлька", "юля",
    "саша", "альберт", "гг", "арчи", "батя", "папа", "мама", "сын", "дочка",
    "кристи", "милa", "дана", "дэн", "дена", "никитава", "лось", "wolf", "vova",
    "sasha", "sanya", "dima", "dmitriy", "dmitry", "denis", "den", "ilya", "ivan",
    "igorf", "kirill", "maks", "maksim", "maxim", "max", "mikhail", "misha", "nikita",
    "oleg", "pasha", "pavel", "petya", "roma", "roman", "serega", "sergey", "slava",
    "timur", "tolya", "yura", "yuri", "vlad", "vladimir", "vitalik", "vitaliy",
    "vasya", "vasiliy", "gena", "goga", "gosha", "grisha", "zheka", "zhenya",
    "andrey", "artem", "anton", "alex", "alexey", "alexander", "kate", "katya",
    "nastya", "nasta", "olya", "olga", "lena", "lena", "masha", "maria", "mary",
    "natasha", "sveta", "tanja", "tanya", "victoria", "vika", "vika", "yana",
}


def char_classes(p):
    classes = 0
    if re.search(r"[a-z]", p):
        classes += 1
    if re.search(r"[A-Z]", p):
        classes += 1
    if re.search(r"\d", p):
        classes += 1
    if re.search(r"[^a-zA-Z0-9]", p):
        classes += 1
    return classes


def entropy_bits(p):
    if not p:
        return 0
    lower = set(p.lower())
    pool = 0
    if any(c.islower() for c in p):
        pool += 26
    if any(c.isupper() for c in p):
        pool += 26
    if any(c.isdigit() for c in p):
        pool += 10
    if any(not c.isalnum() for c in p):
        pool += 33
    per_char = math.log2(max(pool, 1))
    return len(p) * per_char


def normalize(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if c.isascii())


def check_patterns(p):
    issues = []
    lp = p.lower()

    if lp.isdigit():
        issues.append("только цифры — очень слабо для WiFi")
        if re.fullmatch(r"(?:\+?380|0)\d{9}", p):
            issues.append("похоже на украинский номер телефона")

    for year in range(1990, 2027):
        if str(year) in p:
            issues.append(f"содержит год {year} (частая маска)")

    date_patterns = [
        r"\d{2}[.\-/]\d{2}[.\-/]\d{4}",
        r"\d{4}[.\-/]\d{2}[.\-/]\d{2}",
        r"\d{8}",
    ]
    for pat in date_patterns:
        if re.search(pat, p):
            issues.append("похоже на дату (частая маска)")

    seqs = ["qwerty", "йцукен", "123456", "654321", "000000", "111111", "abcabc", "abcdef", "123123"]
    for s in seqs:
        if s in lp:
            issues.append(f"содержит последовательность '{s}'")

    if re.search(r"(.)\1{2,}", lp):
        issues.append("повторяющиеся символы (aa, 111...)")

    if lp in ("password", "пароль", "qwerty", "12345678", "wifipassword", "wifipass", "password123"):
        issues.append("тривиальный пароль")

    return issues


def name_variants(p, dic):
    lp = p.lower()
    core = re.sub(r"[\d\W_]+$", "", lp)
    core = re.sub(r"^[\d\W_]+", "", core)
    for name, translit in [(n, normalize(n)) for n in COMMON_NAMES]:
        if name in lp or (translit and translit in lp):
            suffix = lp.replace(name, "").replace(translit, "")
            if not suffix or re.fullmatch(r"[.\-_!@#$*&0-9]+", suffix):
                return name
    if core in dic and len(p) <= 12:
        return core
    return None


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("=== WiFi Password Auditor ===\n")
    p = sys.argv[1] if len(sys.argv) > 1 else getpass.getpass("Введи пароль (не будет отображаться): ")
    if not p:
        print("Пустой ввод.")
        return 1

    dic = load_dict()
    print(f"\nРазмер словаря: {len(dic)}")

    score = 0
    max_score = 100
    notes = []

    L = len(p)
    if L < 8:
        notes.append(f"длина {L} — меньше 8, для WiFi критично мало")
    elif L < 12:
        notes.append(f"длина {L} — минимум-минимум для WiFi, лучше 12+")
    elif L < 16:
        notes.append(f"длина {L} — нормально, но 16+ надёжнее")
    else:
        notes.append(f"длина {L} — хорошо")

    score += min(35, L * 3)

    cc = char_classes(p)
    score += (cc - 1) * 8
    if cc < 3:
        notes.append(f"всего {cc} класса символов — используй буквы+цифры+спецсимволы")

    bits = entropy_bits(p)
    score += min(25, int(bits / 2))
    notes.append(f"энтропия ~{bits:.0f} бит (оценка по набору символов)")

    lp = p.lower()
    if lp in dic:
        print("\n[КРИТИЧНО] Пароль найден в словаре топ-10000 общих паролей.")
        score -= 60
        notes.append("пароль в топе-10000 самых распространённых")

    elif len(lp.rstrip("0123456789.!@#$%^&*_-")) <= 3:
        base = lp.rstrip("0123456789.!@#$%^&*_-")
        if base in dic:
            print("\n[КРИТИЧНО] Основа пароля в словаре (с добавкой цифр/символов).")
            score -= 50
            notes.append("словарная основа с лёгким «соль-суффиксом»")

    name = name_variants(p, dic)
    if name:
        print(f"\n[ВАЖНО] Пароль основан на имени/слове ({name}) — угадывается перебором имён.")
        score -= 30
        notes.append(f"имя/слово '{name}' в основе")

    for issue in check_patterns(p):
        score -= 12
        notes.append(issue)

    score = max(0, min(max_score, score))

    print("\n" + "=" * 45)
    if score >= 75:
        verdict = "НАДЁЖНЫЙ"
    elif score >= 50:
        verdict = "СРЕДНИЙ"
    else:
        verdict = "СЛАБЫЙ"
    print(f"Оценка: {score}/100 — {verdict}")
    print("=" * 45)
    print("\nАнализ:")
    for n in notes:
        print(f"  - {n}")

    print("\nПроверка честная: словарь топ-10000 + базовые паттерны.")
    print("Это НЕ полный перебор WPA-PSK (полный rockyou/маски = hashcat).")
    return 0


if __name__ == "__main__":
    sys.exit(main())