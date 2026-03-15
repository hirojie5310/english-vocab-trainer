import sys
import csv
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Tuple


@dataclass(frozen=True)
class Vocab:
    en: str
    ja: str
    pos: str = field(default="", compare=False)
    example_en: str = field(default="", compare=False)
    example_ja: str = field(default="", compare=False)


CORRECT_LOG_NAME = "correct_answers_log.csv"


def is_idiom_csv(csv_path: Path) -> bool:
    return "idiom" in csv_path.stem.lower()


def get_here() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent  # exeの場所
    try:
        return Path(__file__).resolve().parent
    except NameError:
        return Path.cwd()


def load_vocab_from_csv(csv_path: Path) -> List[Vocab]:
    """
    CSVを読み込み、語彙情報を返す。
    - 1行に英語と日本語が入っている前提（区切りはカンマ）
    - ヘッダーがあってもOK（英語/日本語っぽい列名なら自動判定を試みる）
    - それ以外は「1列目=英語、2列目=日本語」として読む
    """
    vocab: List[Vocab] = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]

    if not rows:
        raise ValueError("CSVが空です。")

    idiom_dataset = is_idiom_csv(csv_path)

    # ヘッダーっぽいか判定
    header = [c.strip().lower() for c in rows[0]]
    has_header = False
    en_idx, ja_idx = 0, 1
    pos_idx = None
    example_en_idx = None
    example_ja_idx = None

    # よくある列名パターン
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
        # 位置を推定
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

    for r in data_rows:
        if len(r) < 2:
            continue
        en = r[en_idx].strip()
        ja = r[ja_idx].strip()
        if en and ja:
            pos = r[pos_idx].strip() if pos_idx is not None and len(r) > pos_idx else ""
            example_en = (
                r[example_en_idx].strip()
                if example_en_idx is not None and len(r) > example_en_idx
                else ""
            )
            example_ja = (
                r[example_ja_idx].strip()
                if example_ja_idx is not None and len(r) > example_ja_idx
                else ""
            )
            if idiom_dataset:
                # 熟語データでは表示要件に合わせて品詞・例文を無効化する。
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

    # 重複を軽く除去（同一ペア）
    vocab = list(dict.fromkeys(vocab))

    if len(vocab) < 4:
        raise ValueError("4択を作るため、最低4件の単語が必要です。")

    return vocab


def pick_choices(
    vocab_list: List[Vocab], correct: Vocab, mode: int
) -> Tuple[List[str], int]:
    """
    4択（表示する選択肢のリスト）と正解のインデックス(0-3)を返す。
    mode=1: 英→和（選択肢は和訳）
    mode=2: 和→英（選択肢は英単語）
    """
    if mode == 1:
        # 正解の和訳 + 他の和訳3つ
        pool = [v.ja for v in vocab_list if v.ja != correct.ja]
        distractors = random.sample(pool, 3)
        choices = [correct.ja] + distractors
    else:
        # 正解の英単語 + 他の英単語3つ
        pool = [v.en for v in vocab_list if v.en != correct.en]
        distractors = random.sample(pool, 3)
        choices = [correct.en] + distractors

    random.shuffle(choices)
    correct_index = choices.index(correct.ja if mode == 1 else correct.en)
    return choices, correct_index


def format_review_line(
    choices: List[str], vocab_list: List[Vocab], mode: int, show_pos: bool = True
) -> str:
    """
    表示した候補に対して、対応する英語/日本語/品詞を
    1. xxx（品詞, yyy） の形式で連結して返す。
    mode=1: 候補=和訳 → 表示は「英語（品詞, 和訳）」にしたいので、和訳から引く
    mode=2: 候補=英語 → 表示は「英語（品詞, 和訳）」でOK（英語から引く）
    """
    # 検索用dict
    en_to_vocab = {v.en: v for v in vocab_list}
    ja_to_vocab = {v.ja: v for v in vocab_list}

    parts = []
    for i, c in enumerate(choices, start=1):
        if mode == 1:
            # c は和訳
            v = ja_to_vocab.get(c)
            if v:
                pos_part = f"{v.pos}, " if show_pos and v.pos else ""
                parts.append(f"{i}. {v.en}（{pos_part}{v.ja}）")
            else:
                parts.append(f"{i}. ???（{c}）")
        else:
            # c は英語
            v = en_to_vocab.get(c)
            if v:
                pos_part = f"{v.pos}, " if show_pos and v.pos else ""
                parts.append(f"{i}. {v.en}（{pos_part}{v.ja}）")
            else:
                parts.append(f"{i}. {c}（???）")

    return " ".join(parts)


def append_wrong_log(
    log_path: Path,
    mode: int,
    qno: int,
    prompt: str,
    choices: List[str],
    user_answer: int,
    correct_answer: int,
    review_line: str,
) -> None:
    """
    間違えたときのログを追記保存する（Excel文字化け回避で utf-8-sig）。
    """
    is_new = not log_path.exists()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with log_path.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(
                [
                    "timestamp",
                    "mode",
                    "question_no",
                    "prompt",
                    "choices_1",
                    "choices_2",
                    "choices_3",
                    "choices_4",
                    "user_answer_no",
                    "correct_answer_no",
                    "review_line",
                ]
            )
        w.writerow(
            [
                now,
                mode,
                qno,
                prompt,
                choices[0],
                choices[1],
                choices[2],
                choices[3],
                user_answer,
                correct_answer,
                review_line,
            ]
        )


def input_choice() -> int:
    while True:
        s = input("答えの番号（1〜4）: ").strip()
        if s in {"1", "2", "3", "4"}:
            return int(s)
        print("1〜4の数字で入力してください。")


def load_wrong_pairs_from_log(log_path: Path, mode: int) -> list[tuple[str, str]]:
    """
    wrong_answers_log.csv から、指定モードの誤回答（en, ja）ペアを取り出す。

    ログ形式（今回のヘッダー）:
      timestamp,mode,question_no,prompt,choices_1,choices_2,choices_3,choices_4,
      user_answer_no,correct_answer_no,review_line

    復元ルール:
      - mode=1 (英→和): prompt=英単語、正解は choices_{correct_answer_no} の「和訳」
          -> (en, ja) = (prompt, correct_choice_text)
      - mode=2 (和→英): prompt=和訳、正解は choices_{correct_answer_no} の「英単語」
          -> (en, ja) = (correct_choice_text, prompt)
    """
    if not log_path.exists():
        return []

    required = {
        "mode",
        "prompt",
        "correct_answer_no",
        "choices_1",
        "choices_2",
        "choices_3",
        "choices_4",
    }

    pairs: list[tuple[str, str]] = []

    with log_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            # ヘッダーが想定と違う場合は空で返す
            return []

        for row in reader:
            # モード一致チェック
            try:
                row_mode = int((row.get("mode") or "").strip())
            except Exception:
                continue
            if row_mode != mode:
                continue

            prompt = (row.get("prompt") or "").strip()
            if not prompt:
                continue

            # 正解番号（1〜4）を取り出し、choices_{n} から正解テキストを復元
            try:
                correct_no = int((row.get("correct_answer_no") or "").strip())
            except Exception:
                continue
            if correct_no not in (1, 2, 3, 4):
                continue

            correct_text = (row.get(f"choices_{correct_no}") or "").strip()
            if not correct_text:
                continue

            # (en, ja) に揃える
            if mode == 1:
                en, ja = prompt, correct_text
            else:
                en, ja = correct_text, prompt

            pairs.append((en, ja))

    # 重複削除（順序保持）
    return list(dict.fromkeys(pairs))


def build_questions_with_mastery_limit(
    vocab_list: List[Vocab],
    mode: int,
    num_questions: int,
    max_from_wrong: int,
    max_mastered_in_quiz: int,
    wrong_log_path: Path,
    correct_log_path: Path,
) -> Tuple[List[Vocab], set[Vocab]]:
    """
    正解ログを参照して出題を組む。
    - 正解済みは原則除外（不足時のみ max_mastered_in_quiz まで混ぜる）
    - 誤回答ログ由来（wrong）から最大 max_from_wrong まで混ぜる（ただし正解済みは除外）
    - 10問作れない場合は呼び出し側でリセット確認に進めるため、ValueErrorを投げる
    戻り値: (questions, correct_set)
    """
    vocab_set = set(vocab_list)
    correct_set = load_correct_set(correct_log_path)

    unmastered_pool = [v for v in vocab_list if v not in correct_set]
    mastered_pool = [v for v in vocab_list if v in correct_set]

    # wrongログから復習候補（未習得のみ）
    wrong_pairs = load_wrong_pairs_from_log(wrong_log_path, mode)
    wrong_vocab = [Vocab(en=en, ja=ja) for en, ja in wrong_pairs]
    wrong_vocab = [v for v in wrong_vocab if v in vocab_set]
    wrong_vocab = [v for v in wrong_vocab if v not in correct_set]

    random.shuffle(wrong_vocab)
    from_wrong = wrong_vocab[: min(len(wrong_vocab), max_from_wrong)]

    chosen_set = set(from_wrong)
    remaining_needed = num_questions - len(from_wrong)

    unmastered_remaining_pool = [v for v in unmastered_pool if v not in chosen_set]

    if len(unmastered_remaining_pool) >= remaining_needed:
        from_normal = random.sample(unmastered_remaining_pool, remaining_needed)
        questions = from_wrong + from_normal
        random.shuffle(questions)
        return questions, correct_set

    # 未習得だけでは足りない
    questions = from_wrong + unmastered_remaining_pool
    chosen_set = set(questions)
    remaining_needed = num_questions - len(questions)

    if remaining_needed > 0:
        allow = min(remaining_needed, max_mastered_in_quiz)
        mastered_candidates = [v for v in mastered_pool if v not in chosen_set]
        if len(mastered_candidates) >= allow:
            questions += random.sample(mastered_candidates, allow)

    if len(questions) < num_questions:
        raise ValueError("insufficient_questions")

    random.shuffle(questions)
    return questions[:num_questions], correct_set


def load_correct_set(correct_log_path: Path) -> set[Vocab]:
    """
    correct_answers_log.csv から正解済み単語を読み込んで set[Vocab] で返す。
    ファイルがなければ空set。
    """
    if not correct_log_path.exists():
        return set()

    correct_set: set[Vocab] = set()
    with correct_log_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return set()

        # 想定ヘッダー: timestamp,en,ja
        for row in reader:
            en = (row.get("en") or "").strip()
            ja = (row.get("ja") or "").strip()
            if en and ja:
                correct_set.add(Vocab(en=en, ja=ja))

    return correct_set


def append_correct_log(correct_log_path: Path, v: Vocab) -> None:
    """
    正解した単語を correct_answers_log.csv に追記（Excel向け utf-8-sig）。
    重複行が増えるのを避けたい場合は、呼び出し側で「未登録時のみ追記」する。
    """
    is_new = not correct_log_path.exists()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with correct_log_path.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["timestamp", "en", "ja"])
        w.writerow([now, v.en, v.ja])


def confirm_yes_no(prompt: str, default_no: bool = True) -> bool:
    """
    y / n を受け取る確認入力。
    default_no=True なら Enter は No 扱い、False なら Enter は Yes 扱い。
    """
    suffix = " [y/N]: " if default_no else " [Y/n]: "
    while True:
        s = input(prompt + suffix).strip().lower()
        if s == "" and default_no:
            return False
        if s == "" and not default_no:
            return True
        if s in {"y", "yes"}:
            return True
        if s in {"n", "no"}:
            return False
        print("y か n で入力してください。")


def reset_correct_log(correct_log_path: Path) -> None:
    """
    正解ログを空にする（ファイル削除）。
    """
    if correct_log_path.exists():
        correct_log_path.unlink()


# CSVを選ばせる
def select_vocab_csv(base_dir):
    # 学習用CSVを取得（vocab*.csv / eiken*.csv）
    csv_files = sorted(
        [
            p
            for p in base_dir.glob("*.csv")
            if (p.name.startswith("vocab") or p.name.startswith("eiken"))
            and p.name not in {"wrong_answers_log.csv", CORRECT_LOG_NAME}
        ]
    )

    if not csv_files:
        print("学習用CSVファイルが見つかりません。")
        print("同じフォルダに vocab*.csv または eiken*.csv を置いてください。")
        raise SystemExit

    print("使用するCSVファイルを選択してください:")
    for i, path in enumerate(csv_files):
        idiom_label = "（熟語）" if is_idiom_csv(path) else ""
        print(f"{i}. {path.name}{idiom_label}")

    while True:
        s = input(f"番号を入力してください（0～{len(csv_files) - 1}）: ").strip()
        if s.isdigit():
            idx = int(s)
            if 0 <= idx < len(csv_files):
                return csv_files[idx]
        print("正しい番号を入力してください。")


def main():
    base_dir = get_here()

    # vocab*.csv を候補として選択
    csv_path = select_vocab_csv(base_dir)
    is_idiom_dataset = is_idiom_csv(csv_path)
    print(f"選択されたCSV: {csv_path.name}")

    vocab_list = load_vocab_from_csv(csv_path)

    # モード選択
    print("モードを選択してください")
    source_label = "英熟語" if is_idiom_dataset else "英単語"
    print(f"1: {source_label} → 和訳（4択）")
    print(f"2: 和訳 → {source_label}（4択）")
    while True:
        mode_s = input("モード（1 or 2）: ").strip()
        if mode_s in {"1", "2"}:
            mode = int(mode_s)
            break
        print("1 または 2 を入力してください。")

    # ----------------- 出題リスト作成ブロック
    num_questions = 10
    max_from_wrong = num_questions // 2  # 最大5問
    max_mastered_in_quiz = 2  # 正解済みを混ぜる上限（2問以内）

    wrong_log_path = base_dir / "wrong_answers_log.csv"
    correct_log_path = base_dir / CORRECT_LOG_NAME

    # --- 出題リストを作る（不足なら正解ログのリセットを提案） ---
    try:
        questions, correct_set = build_questions_with_mastery_limit(
            vocab_list=vocab_list,
            mode=mode,
            num_questions=num_questions,
            max_from_wrong=max_from_wrong,
            max_mastered_in_quiz=max_mastered_in_quiz,
            wrong_log_path=wrong_log_path,
            correct_log_path=correct_log_path,
        )
    except ValueError:
        # 10問作れない＝正解ログが溜まりすぎ
        mastered_count = len(load_correct_set(correct_log_path) & set(vocab_list))
        total_count = len(vocab_list)
        print("\n出題可能な未習得単語が不足して、10問を作れませんでした。")
        print(f"現在の正解済み単語数: {mastered_count}/{total_count}")

        if confirm_yes_no(
            "正解ログをリセットして続行しますか？（正解済み扱いを解除）",
            default_no=True,
        ):
            reset_correct_log(correct_log_path)
            print("正解ログをリセットしました。")

            # 再作成（今度は作れるはず）
            questions, correct_set = build_questions_with_mastery_limit(
                vocab_list=vocab_list,
                mode=mode,
                num_questions=num_questions,
                max_from_wrong=max_from_wrong,
                max_mastered_in_quiz=max_mastered_in_quiz,
                wrong_log_path=wrong_log_path,
                correct_log_path=correct_log_path,
            )
        else:
            print("終了します。")
            raise SystemExit
    # -----------------

    correct_count = 0

    for i, correct in enumerate(questions, start=1):
        if mode == 1:
            prompt = correct.en
            print(f"\n【第{i}問】")
            pos_text = (
                f", {correct.pos}" if (not is_idiom_dataset and correct.pos) else ""
            )
            print(f"問題: {prompt}{pos_text}")
        else:
            prompt = correct.ja
            print(f"\n【第{i}問】")
            pos_text = (
                f", {correct.pos}" if (not is_idiom_dataset and correct.pos) else ""
            )
            print(f"問題: {prompt}{pos_text}")

        choices, correct_idx0 = pick_choices(vocab_list, correct, mode)

        for n, c in enumerate(choices, start=1):
            print(f"{n}. {c}")

        ans = input_choice()
        is_correct = ans - 1 == correct_idx0

        if is_correct:
            print("正解！")
            correct_count += 1

            # 正解済みとして記録（すでに正解済みなら二重に書かない）
            if correct not in correct_set:
                append_correct_log(correct_log_path, correct)
                correct_set.add(
                    correct
                )  # 今回セッション中も即反映（以降の出題抑制に効く）
        else:
            print(f"間違いです。正解は{correct_idx0 + 1}番です。")

        # 確認用の「候補＋対応」を表示
        review_line = format_review_line(
            choices, vocab_list, mode, show_pos=not is_idiom_dataset
        )
        print(review_line)

        if not is_idiom_dataset and correct.example_en:
            if correct.example_ja:
                print(f"例文: {correct.example_en} ({correct.example_ja})")
            else:
                print(f"例文: {correct.example_en}")

        # 間違えたときはログ保存
        if not is_correct:
            append_wrong_log(
                log_path=wrong_log_path,
                mode=mode,
                qno=i,
                prompt=prompt,
                choices=choices,
                user_answer=ans,
                correct_answer=correct_idx0 + 1,
                review_line=review_line,
            )

    accuracy = (correct_count / num_questions) * 100
    print("\n==== 結果 ====")
    print(f"正解数: {correct_count}/{num_questions}")
    print(f"正答率: {accuracy:.1f}%")
    print(f"間違いログ: {wrong_log_path}（間違えた問題がある場合のみ追記されています）")

    # --- クイズ終了後：正解済み単語数/全単語数を表示し、リセット確認 ---
    current_correct_set = load_correct_set(correct_log_path)
    mastered_count = len(current_correct_set & set(vocab_list))
    total_count = len(vocab_list)

    print(f"\n現在の正解済み単語数: {mastered_count}/{total_count}")

    if mastered_count > 0:
        if confirm_yes_no(
            "正解ログを消去しますか？（次回は正解済み単語も出題対象に戻ります）",
            default_no=True,
        ):
            reset_correct_log(correct_log_path)
            print("正解ログを消去しました。")
        else:
            print("正解ログは保持します。")


if __name__ == "__main__":
    main()
