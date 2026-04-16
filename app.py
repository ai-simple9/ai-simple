from flask import Flask, request, jsonify, send_from_directory
import json
import os
import random
import re
import shutil
from datetime import datetime
from difflib import SequenceMatcher

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_FILE = os.path.join(BASE_DIR, "knowledge.json")
MEMORY_FILE = os.path.join(BASE_DIR, "memory.json")
DIALOG_FILE = os.path.join(BASE_DIR, "dialog_memory.json")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

app = Flask(__name__, static_folder=None)


def ensure_dirs():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def load_json(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def backup_knowledge():
    ensure_dirs()
    if os.path.exists(KNOWLEDGE_FILE):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"knowledge_{ts}.json")
        shutil.copyfile(KNOWLEDGE_FILE, backup_path)
        return os.path.basename(backup_path)
    return None


knowledge = load_json(KNOWLEDGE_FILE, {
    "categories": {
        "greetings": {
            "keywords": ["привет", "здарова", "салам", "хай", "hello"],
            "answers": [
                "Привет.",
                "Здарова.",
                "Салам.",
                "Привет. Пиши нормально."
            ]
        },
        "about_bot": {
            "keywords": ["кто ты", "что ты", "что умеешь", "умеешь"],
            "answers": [
                "Я demo railway bot — локальный чат на Flask.",
                "Я работаю по базе знаний, памяти, рейтингу и похожим вопросам.",
                "Я не LLM, но для простого своего бота уже норм."
            ]
        },
        "coding": {
            "keywords": ["python", "код", "программирование", "сайт", "html", "js", "flask"],
            "answers": [
                "Flask + HTML + JS — нормальный старт.",
                "Хочешь умнее бота — расширяй базу знаний и чисти мусорные пары.",
                "Без хорошей базы знаний бот будет слабый."
            ]
        }
    },
    "custom_pairs": [
        {
            "id": 1,
            "question": "как тебя зовут",
            "answers": ["Меня зовут demo railway bot."],
            "tags": ["bot", "name"],
            "rating_up": 0,
            "rating_down": 0,
            "is_active": True,
            "created_at": "2026-04-17 00:00:00",
            "updated_at": "2026-04-17 00:00:00"
        },
        {
            "id": 2,
            "question": "что такое python",
            "answers": [
                "Python — это язык программирования.",
                "Python удобен для автоматизации, сайтов и ботов."
            ],
            "tags": ["python", "code"],
            "rating_up": 0,
            "rating_down": 0,
            "is_active": True,
            "created_at": "2026-04-17 00:00:00",
            "updated_at": "2026-04-17 00:00:00"
        }
    ],
    "last_id": 2,
    "settings": {
        "auto_disable_threshold": 3
    }
})

memory = load_json(MEMORY_FILE, {})
dialog_memory = load_json(DIALOG_FILE, [])


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\sа-яё]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str):
    return normalize(text).split()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def keyword_overlap_score(a: str, b: str) -> float:
    words_a = set(tokenize(a))
    words_b = set(tokenize(b))
    if not words_a or not words_b:
        return 0.0
    common = words_a.intersection(words_b)
    union = words_a.union(words_b)
    return len(common) / len(union)


def combined_score(user_text: str, saved_question: str) -> float:
    return (similarity(user_text, saved_question) * 0.7) + (keyword_overlap_score(user_text, saved_question) * 0.3)


def persist_knowledge(with_backup=False):
    if with_backup:
        backup_knowledge()
    save_json(KNOWLEDGE_FILE, knowledge)


def remember_dialog(user_text, bot_text, source_type="fallback", pair_id=None):
    dialog_memory.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user_text,
        "bot": bot_text,
        "source_type": source_type,
        "pair_id": pair_id
    })
    if len(dialog_memory) > 50:
        del dialog_memory[:-50]
    save_json(DIALOG_FILE, dialog_memory)


def get_recent_context():
    return dialog_memory[-4:] if dialog_memory else []


def get_memory_reply(text):
    norm = normalize(text)

    if norm.startswith("меня зовут "):
        name = text[len("меня зовут "):].strip()
        if name:
            memory["name"] = name
            save_json(MEMORY_FILE, memory)
            return f"Запомнил. Тебя зовут {name}."

    if norm == "как меня зовут":
        if "name" in memory:
            return f"Тебя зовут {memory['name']}."
        return "Я пока не знаю твоё имя."

    if norm.startswith("запомни что "):
        fact = text[len("запомни что "):].strip()
        if fact:
            memory.setdefault("facts", []).append(fact)
            save_json(MEMORY_FILE, memory)
            return f"Запомнил: {fact}"

    if norm == "что ты помнишь":
        parts = []
        if memory.get("name"):
            parts.append(f"Имя: {memory['name']}")
        if memory.get("facts"):
            parts.append("Факты: " + ", ".join(memory["facts"][-5:]))
        if not parts:
            return "Пока ничего полезного не помню."
        return "Я помню:\n" + "\n".join(parts)

    if norm == "очистить память":
        memory.clear()
        save_json(MEMORY_FILE, memory)
        return "Память очищена."

    if norm == "очистить диалог":
        dialog_memory.clear()
        save_json(DIALOG_FILE, dialog_memory)
        return "Память диалога очищена."

    return None


def get_active_pairs():
    return [p for p in knowledge.get("custom_pairs", []) if p.get("is_active", True)]


def find_exact_custom_answer(text):
    norm = normalize(text)
    for pair in get_active_pairs():
        if normalize(pair.get("question", "")) == norm:
            return pair
    return None


def find_top_similar_pairs(text, threshold=0.42, limit=5):
    scored = []
    for pair in get_active_pairs():
        score = combined_score(text, pair.get("question", ""))
        if score >= threshold:
            rating_balance = pair.get("rating_up", 0) - pair.get("rating_down", 0)
            scored.append((score, rating_balance, pair))
    scored.sort(key=lambda x: (x[0], x[1], x[2].get("rating_up", 0)), reverse=True)
    return scored[:limit]


def choose_best_pair(top_pairs):
    if not top_pairs:
        return None
    best_score, _, best_pair = top_pairs[0]
    if len(top_pairs) > 1:
        second_score, _, second_pair = top_pairs[1]
        if abs(best_score - second_score) < 0.05:
            ordered = sorted(
                [best_pair, second_pair],
                key=lambda p: (p.get("rating_up", 0) - p.get("rating_down", 0), len(p.get("answers", []))),
                reverse=True
            )
            return ordered[0]
    return best_pair


def pick_answer_from_pair(pair):
    answers = pair.get("answers", [])
    if not answers:
        return "У этой пары нет ответа."
    return random.choice(answers)


def find_category_answer(text):
    norm = normalize(text)
    categories = knowledge.get("categories", {})
    best_category = None
    best_hits = 0
    for _, category_data in categories.items():
        hits = 0
        for keyword in category_data.get("keywords", []):
            if normalize(keyword) in norm:
                hits += 1
        if hits > best_hits:
            best_hits = hits
            best_category = category_data
    if best_category and best_category.get("answers"):
        return random.choice(best_category["answers"])
    return None


def fallback_answer(user_text):
    recent = get_recent_context()
    if recent:
        topics = " | ".join(item["user"] for item in recent)
        return f"Точного ответа нет. Недавний контекст: {topics}. Либо уточни, либо обучи меня новой паре."
    return random.choice([
        "Не понял нормально. Уточни или добавь обучение.",
        "В базе нет хорошего ответа на это.",
        "Пока слабо понял. Добавь вопрос и ответ в базу.",
        "Такого ответа у меня пока нет."
    ])


def auto_disable_bad_pairs():
    threshold = knowledge.get("settings", {}).get("auto_disable_threshold", 3)
    changed = False
    for pair in knowledge.get("custom_pairs", []):
        balance = pair.get("rating_down", 0) - pair.get("rating_up", 0)
        if balance >= threshold and pair.get("is_active", True):
            pair["is_active"] = False
            pair["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            changed = True
    if changed:
        persist_knowledge(with_backup=True)


def generate_reply(user_text):
    auto_disable_bad_pairs()

    memory_reply = get_memory_reply(user_text)
    if memory_reply:
        return {"reply": memory_reply, "source_type": "memory", "pair_id": None}

    exact_pair = find_exact_custom_answer(user_text)
    if exact_pair:
        return {"reply": pick_answer_from_pair(exact_pair), "source_type": "exact", "pair_id": exact_pair["id"]}

    top_pairs = find_top_similar_pairs(user_text)
    best_pair = choose_best_pair(top_pairs)
    if best_pair:
        return {"reply": pick_answer_from_pair(best_pair), "source_type": "similar", "pair_id": best_pair["id"]}

    category_answer = find_category_answer(user_text)
    if category_answer:
        return {"reply": category_answer, "source_type": "category", "pair_id": None}

    return {"reply": fallback_answer(user_text), "source_type": "fallback", "pair_id": None}


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/style.css")
def style_css():
    return send_from_directory(BASE_DIR, "style.css", mimetype="text/css")


@app.route("/script.js")
def script_js():
    return send_from_directory(BASE_DIR, "script.js", mimetype="application/javascript")


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = str(data.get("message", "")).strip()
    if not user_message:
        return jsonify({"reply": "Пустое сообщение — мусор. Напиши нормально."}), 400

    result = generate_reply(user_message)
    remember_dialog(user_message, result["reply"], result["source_type"], result["pair_id"])
    return jsonify(result)


@app.route("/train", methods=["POST"])
def train():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    answers_raw = data.get("answers", [])
    tags_raw = data.get("tags", [])

    if not question or not isinstance(answers_raw, list) or not answers_raw:
        return jsonify({"status": "error", "message": "Нужен вопрос и хотя бы один ответ."}), 400

    answers = [str(a).strip() for a in answers_raw if str(a).strip()]
    tags = [str(t).strip().lower() for t in tags_raw if str(t).strip()]
    if not answers:
        return jsonify({"status": "error", "message": "Ответы пустые."}), 400

    next_id = knowledge.get("last_id", 0) + 1
    knowledge["last_id"] = next_id
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    knowledge.setdefault("custom_pairs", []).append({
        "id": next_id,
        "question": question,
        "answers": answers,
        "tags": tags,
        "rating_up": 0,
        "rating_down": 0,
        "is_active": True,
        "created_at": now,
        "updated_at": now
    })
    persist_knowledge(with_backup=True)
    return jsonify({"status": "success", "message": f"Добавлено обучение: {question}"})


@app.route("/history")
def history():
    return jsonify({"dialog": dialog_memory})


@app.route("/knowledge")
def get_knowledge():
    q = request.args.get("q", "").strip().lower()
    tag = request.args.get("tag", "").strip().lower()

    pairs = knowledge.get("custom_pairs", [])
    if q:
        pairs = [
            p for p in pairs
            if q in p.get("question", "").lower() or any(q in a.lower() for a in p.get("answers", []))
        ]
    if tag:
        pairs = [p for p in pairs if tag in [t.lower() for t in p.get("tags", [])]]

    return jsonify({
        "categories": knowledge.get("categories", {}),
        "custom_pairs": pairs,
        "last_id": knowledge.get("last_id", 0),
        "settings": knowledge.get("settings", {})
    })


@app.route("/knowledge/delete", methods=["POST"])
def delete_knowledge():
    data = request.get_json(silent=True) or {}
    pair_id = data.get("id")
    if pair_id is None:
        return jsonify({"status": "error", "message": "Нет id."}), 400

    before = len(knowledge.get("custom_pairs", []))
    knowledge["custom_pairs"] = [p for p in knowledge.get("custom_pairs", []) if p.get("id") != pair_id]
    after = len(knowledge.get("custom_pairs", []))
    if before == after:
        return jsonify({"status": "error", "message": "Запись не найдена."}), 404

    persist_knowledge(with_backup=True)
    return jsonify({"status": "success", "message": f"Удалено: {pair_id}"})


@app.route("/knowledge/update", methods=["POST"])
def update_knowledge():
    data = request.get_json(silent=True) or {}
    pair_id = data.get("id")
    question = str(data.get("question", "")).strip()
    answers = data.get("answers", [])
    tags = data.get("tags", [])
    is_active = data.get("is_active", True)

    if pair_id is None or not question or not isinstance(answers, list) or not answers:
        return jsonify({"status": "error", "message": "Неверные данные для обновления."}), 400

    answers = [str(a).strip() for a in answers if str(a).strip()]
    tags = [str(t).strip().lower() for t in tags if str(t).strip()]

    for pair in knowledge.get("custom_pairs", []):
        if pair.get("id") == pair_id:
            pair["question"] = question
            pair["answers"] = answers
            pair["tags"] = tags
            pair["is_active"] = bool(is_active)
            pair["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            persist_knowledge(with_backup=True)
            return jsonify({"status": "success", "message": f"Обновлено: {pair_id}"})

    return jsonify({"status": "error", "message": "Пара не найдена."}), 404


@app.route("/rate", methods=["POST"])
def rate_answer():
    data = request.get_json(silent=True) or {}
    pair_id = data.get("pair_id")
    vote = data.get("vote")

    if pair_id is None or vote not in ["up", "down"]:
        return jsonify({"status": "error", "message": "Неверные данные."}), 400

    for pair in knowledge.get("custom_pairs", []):
        if pair.get("id") == pair_id:
            if vote == "up":
                pair["rating_up"] = pair.get("rating_up", 0) + 1
            else:
                pair["rating_down"] = pair.get("rating_down", 0) + 1
            pair["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            persist_knowledge(with_backup=True)
            auto_disable_bad_pairs()
            return jsonify({
                "status": "success",
                "message": "Оценка сохранена.",
                "rating_up": pair["rating_up"],
                "rating_down": pair["rating_down"],
                "is_active": pair.get("is_active", True)
            })

    return jsonify({"status": "error", "message": "Пара не найдена."}), 404


@app.route("/knowledge/import", methods=["POST"])
def import_knowledge():
    data = request.get_json(silent=True) or {}
    imported = data.get("custom_pairs")
    if not isinstance(imported, list):
        return jsonify({"status": "error", "message": "Нужен список custom_pairs."}), 400

    count = 0
    last_id = knowledge.get("last_id", 0)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in imported:
        question = str(item.get("question", "")).strip()
        answers = item.get("answers", [])
        tags = item.get("tags", [])
        if not question:
            continue
        if isinstance(answers, str):
            answers = [answers]
        answers = [str(a).strip() for a in answers if str(a).strip()]
        tags = [str(t).strip().lower() for t in tags if str(t).strip()]
        if not answers:
            continue
        last_id += 1
        knowledge.setdefault("custom_pairs", []).append({
            "id": last_id,
            "question": question,
            "answers": answers,
            "tags": tags,
            "rating_up": 0,
            "rating_down": 0,
            "is_active": True,
            "created_at": now,
            "updated_at": now
        })
        count += 1

    knowledge["last_id"] = last_id
    persist_knowledge(with_backup=True)
    return jsonify({"status": "success", "message": f"Импортировано: {count}"})


@app.route("/knowledge/backup", methods=["POST"])
def create_backup():
    path = backup_knowledge()
    if not path:
        return jsonify({"status": "error", "message": "Файл knowledge.json не найден."}), 404
    return jsonify({"status": "success", "message": "Резервная копия создана.", "path": path})


@app.route("/backups")
def list_backups():
    ensure_dirs()
    files = sorted(os.listdir(BACKUP_DIR), reverse=True)
    return jsonify({"files": files})


if __name__ == "__main__":
    ensure_dirs()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)