import csv
import hashlib
import json
import random
from dataclasses import dataclass, field
from io import StringIO
from typing import List, Tuple


@dataclass(frozen=True)
class Vocab:
    en: str
    ja: str
    pos: str = field(default="", compare=False)
    example_en: str = field(default="", compare=False)
    example_ja: str = field(default="", compare=False)


def is_idiom_filename(filename: str) -> bool:
    return "idiom" in filename.lower()


def compute_dataset_id(filename: str, csv_text: str) -> str:
    digest = hashlib.sha1(f"{filename}\n{csv_text}".encode("utf-8")).hexdigest()
    return digest[:16]


def load_vocab_from_text(csv_text: str, filename: str) -> List[Vocab]:
    rows = []
    reader = csv.reader(StringIO(csv_text))
    for row in reader:
        if row and any(cell.strip() for cell in row):
            rows.append(row)

    if not rows:
        raise ValueError("CSVが空です。")

    idiom_dataset = is_idiom_filename(filename)
    header = [c.strip().lower() for c in rows[0]]
    has_header = False
    en_idx, ja_idx = 0, 1
    pos_idx = None
    example_en_idx = None
    example_ja_idx = None

    en_candidates = {"en", "eng", "english", "word", "単語", "英語", "idiom", "熟語"}
    ja_candidates = {"ja", "jp", "japanese", "meaning", "訳", "和訳", "日本語", "意味"}
    pos_candidates = {"pos", "partofspeech", "品詞"}
    example_en_candidates = {
        "example_en",
        "example",
        "sentence",
        "exampleenglish",
        "例文",
    }
    example_ja_candidates = {
        "example_ja",
        "example_jp",
        "examplejapanese",
        "例文和訳",
        "和訳例文",
    }

    if (
        len(header) >= 2
        and (set(header) & en_candidates)
        and (set(header) & ja_candidates)
    ):
        has_header = True
        for i, name in enumerate(header):
            if name in en_candidates:
                en_idx = i
            if name in ja_candidates:
                ja_idx = i
            if name in pos_candidates:
                pos_idx = i
            if name in example_en_candidates:
                example_en_idx = i
            if name in example_ja_candidates:
                example_ja_idx = i

    data_rows = rows[1:] if has_header else rows
    vocab: List[Vocab] = []
    for row in data_rows:
        if len(row) < 2:
            continue
        en = row[en_idx].strip()
        ja = row[ja_idx].strip()
        if not en or not ja:
            continue

        pos = row[pos_idx].strip() if pos_idx is not None and len(row) > pos_idx else ""
        example_en = (
            row[example_en_idx].strip()
            if example_en_idx is not None and len(row) > example_en_idx
            else ""
        )
        example_ja = (
            row[example_ja_idx].strip()
            if example_ja_idx is not None and len(row) > example_ja_idx
            else ""
        )

        if idiom_dataset:
            pos = ""
            example_en = ""
            example_ja = ""

        vocab.append(
            Vocab(
                en=en,
                ja=ja,
                pos=pos,
                example_en=example_en,
                example_ja=example_ja,
            )
        )

    vocab = list(dict.fromkeys(vocab))
    if len(vocab) < 4:
        raise ValueError("4択を作るため、最低4件の単語が必要です。")
    return vocab


def pick_choices(
    vocab_list: List[Vocab], correct: Vocab, mode: int
) -> Tuple[List[str], int]:
    if mode == 1:
        pool = [v.ja for v in vocab_list if v.ja != correct.ja]
        choices = [correct.ja] + random.sample(pool, 3)
        answer = correct.ja
    else:
        pool = [v.en for v in vocab_list if v.en != correct.en]
        choices = [correct.en] + random.sample(pool, 3)
        answer = correct.en

    random.shuffle(choices)
    return choices, choices.index(answer)


def format_review_line(choices: List[str], vocab_list: List[Vocab], mode: int) -> str:
    en_to_vocab = {v.en: v for v in vocab_list}
    ja_to_vocab = {v.ja: v for v in vocab_list}
    parts = []

    for i, choice in enumerate(choices, start=1):
        vocab = ja_to_vocab.get(choice) if mode == 1 else en_to_vocab.get(choice)
        if not vocab:
            parts.append(f"{i}. {choice}")
            continue
        pos_part = f"{vocab.pos}, " if vocab.pos else ""
        parts.append(f"{i}. {vocab.en}（{pos_part}{vocab.ja}）")

    return " ".join(parts)


def parse_csv_text(filename: str, csv_text: str) -> str:
    vocab_list = load_vocab_from_text(csv_text, filename)
    dataset_id = compute_dataset_id(filename, csv_text)
    payload = {
        "dataset_id": dataset_id,
        "filename": filename,
        "is_idiom_dataset": is_idiom_filename(filename),
        "vocab": [
            {
                "en": v.en,
                "ja": v.ja,
                "pos": v.pos,
                "example_en": v.example_en,
                "example_ja": v.example_ja,
            }
            for v in vocab_list
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def _correct_set_from_log(correct_log: list[dict]) -> set[Vocab]:
    correct_set = set()
    for item in correct_log:
        en = (item.get("en") or "").strip()
        ja = (item.get("ja") or "").strip()
        if en and ja:
            correct_set.add(Vocab(en=en, ja=ja))
    return correct_set


def _wrong_pairs_from_log(wrong_log: list[dict], mode: int) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for item in wrong_log:
        if int(item.get("mode", 0)) != mode:
            continue
        en = (item.get("en") or "").strip()
        ja = (item.get("ja") or "").strip()
        if en and ja:
            pairs.append((en, ja))
    return list(dict.fromkeys(pairs))


def build_quiz(
    vocab_json: str,
    mode: int,
    correct_log_json: str = "[]",
    wrong_log_json: str = "[]",
    num_questions: int = 10,
    max_from_wrong: int = 5,
    max_mastered_in_quiz: int = 2,
) -> str:
    data = json.loads(vocab_json)
    vocab_list = [Vocab(**item) for item in data["vocab"]]
    correct_log = json.loads(correct_log_json or "[]")
    wrong_log = json.loads(wrong_log_json or "[]")

    vocab_set = set(vocab_list)
    correct_set = _correct_set_from_log(correct_log)
    unmastered_pool = [v for v in vocab_list if v not in correct_set]
    mastered_pool = [v for v in vocab_list if v in correct_set]

    wrong_pairs = _wrong_pairs_from_log(wrong_log, mode)
    wrong_vocab = [Vocab(en=en, ja=ja) for en, ja in wrong_pairs]
    wrong_vocab = [v for v in wrong_vocab if v in vocab_set and v not in correct_set]
    random.shuffle(wrong_vocab)

    questions = wrong_vocab[: min(len(wrong_vocab), max_from_wrong)]
    chosen_set = set(questions)
    remaining_needed = num_questions - len(questions)

    unmastered_remaining_pool = [v for v in unmastered_pool if v not in chosen_set]
    if len(unmastered_remaining_pool) >= remaining_needed:
        questions += random.sample(unmastered_remaining_pool, remaining_needed)
    else:
        questions += unmastered_remaining_pool
        chosen_set = set(questions)
        remaining_needed = num_questions - len(questions)
        if remaining_needed > 0:
            allow = min(remaining_needed, max_mastered_in_quiz)
            mastered_candidates = [v for v in mastered_pool if v not in chosen_set]
            if len(mastered_candidates) >= allow:
                questions += random.sample(mastered_candidates, allow)

    if len(questions) < num_questions:
        raise ValueError("出題可能な未習得単語が不足しています。正解ログを消去すると再出題できます。")

    random.shuffle(questions)
    quiz_items = []
    for vocab in questions[:num_questions]:
        choices, correct_index = pick_choices(vocab_list, vocab, mode)
        prompt = vocab.en if mode == 1 else vocab.ja
        quiz_items.append(
            {
                "prompt": prompt,
                "pos": vocab.pos,
                "choices": choices,
                "correct_index": correct_index,
                "review_line": format_review_line(choices, vocab_list, mode),
                "example_en": vocab.example_en,
                "example_ja": vocab.example_ja,
                "en": vocab.en,
                "ja": vocab.ja,
            }
        )

    payload = {
        "mode": mode,
        "num_questions": num_questions,
        "is_idiom_dataset": data["is_idiom_dataset"],
        "mastered_count": len(correct_set & set(vocab_list)),
        "total_count": len(vocab_list),
        "questions": quiz_items,
    }
    return json.dumps(payload, ensure_ascii=False)


if __name__ == "__main__":
    print("web_app.py は単体起動用ではありません。")
    print("次のコマンドでローカルサーバーを起動してください:")
    print("  python -m http.server 8000")
    print("そのあと、ブラウザで http://localhost:8000 を開いてください。")
