import os, json, sqlite3, time, asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.environ["BOT_TOKEN"]
DB = os.getenv("DB_PATH", "mocktest.db")
TEST_SECONDS = 45 * 60
QUESTIONS = json.load(open("questions.json", encoding="utf-8"))

def db():
    return sqlite3.connect(DB)

def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS attempts(
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            q_index INTEGER DEFAULT 0, score REAL DEFAULT 0,
            correct INTEGER DEFAULT 0, wrong INTEGER DEFAULT 0,
            skipped INTEGER DEFAULT 0, started REAL, finished INTEGER DEFAULT 0
        )""")

def display_name(u):
    return ("@" + u.username) if u.username else (u.first_name or "Telegram User")

def keyboard(qi):
    return InlineKeyboardMarkup([[InlineKeyboardButton(f"{chr(65+i)}. {opt}", callback_data=f"ans:{qi}:{i}")]
                                 for i,opt in enumerate(QUESTIONS[qi]["o"])])

async def show_question(target, qi):
    q = QUESTIONS[qi]
    await target.reply_text(
        f"📘 ଚନ୍ଦ୍ରମାର ଚୂଡ଼ି | Question {qi+1}/50\n\n{q['q']}",
        reply_markup=keyboard(qi)
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    with db() as c:
        row = c.execute("SELECT finished FROM attempts WHERE user_id=?", (u.id,)).fetchone()
        if row and row[0] == 0:
            c.execute("UPDATE attempts SET username=?, first_name=? WHERE user_id=?",
                      (u.username, u.first_name, u.id))
            qi = c.execute("SELECT q_index FROM attempts WHERE user_id=?", (u.id,)).fetchone()[0]
            if qi < 50:
                await update.message.reply_text("ତୁମର Test ଚାଲୁ ଅଛି।")
                await show_question(update.message, qi)
                return
        c.execute("""INSERT OR REPLACE INTO attempts
          (user_id,username,first_name,q_index,score,correct,wrong,skipped,started,finished)
          VALUES(?,?,?,0,0,0,0,0,?,0)""", (u.id,u.username,u.first_name,time.time()))
    await update.message.reply_text(
        "🎓 OAVS ODISHA TGT MOCK TEST\n📖 ‘ଚନ୍ଦ୍ରମାର ଚୂଡ଼ି’ – ରମାକାନ୍ତ ରଥ\n\n"
        "ମୋଟ ପ୍ରଶ୍ନ: 50 | ସମୟ: 45 ମିନିଟ୍\n"
        "ସଠିକ୍: +1 | ଭୁଲ୍: −0.25 | ଛାଡ଼ିଲେ: 0\n\n"
        "Test ଆରମ୍ଭ କରିବାକୁ /start ପୁଣି ପଠାଅ ନୁହେଁ — ତଳର Start Test ଦବାଅ।",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Start Test", callback_data="begin")]])
    )

async def begin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    u = query.from_user
    with db() as c:
        c.execute("""INSERT OR REPLACE INTO attempts
          (user_id,username,first_name,q_index,score,correct,wrong,skipped,started,finished)
          VALUES(?,?,?,0,0,0,0,0,?,0)""", (u.id,u.username,u.first_name,time.time()))
    await query.edit_message_text("Test ଆରମ୍ଭ ହେଲା! ପ୍ରତ୍ୟେକ ପ୍ରଶ୍ନର ଗୋଟିଏ ଉତ୍ତର ବାଛ।")
    await show_question(query.message, 0)

async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        _, qstr, astr = query.data.split(":")
        qi, ai = int(qstr), int(astr)
    except Exception:
        return
    u = query.from_user
    with db() as c:
        row = c.execute("SELECT q_index,score,correct,wrong,skipped,started,finished FROM attempts WHERE user_id=?", (u.id,)).fetchone()
        if not row or row[6]:
            await query.edit_message_text("ଏହି Test ସମାପ୍ତ ହୋଇଛି। /result କିମ୍ବା /leaderboard ଦେଖ।")
            return
        current, score, correct, wrong, skipped, started, finished = row
        if qi != current:
            await query.answer("ଏହି ପ୍ରଶ୍ନର ଉତ୍ତର ଦିଆଯାଇଛି କିମ୍ବା ପୁରୁଣା ପ୍ରଶ୍ନ।", show_alert=True)
            return
        if time.time() - started > TEST_SECONDS:
            c.execute("UPDATE attempts SET finished=1 WHERE user_id=?", (u.id,))
            await query.edit_message_text("⏰ ସମୟ ସମାପ୍ତ! /result ରେ ଫଳାଫଳ ଦେଖ।")
            return
        right = QUESTIONS[qi]["a"]
        if ai == right:
            score += 1; correct += 1
            feedback = "✅ ସଠିକ୍ ଉତ୍ତର!"
        else:
            score -= 0.25; wrong += 1
            feedback = f"❌ ଭୁଲ୍ ଉତ୍ତର। ସଠିକ୍ ଉତ୍ତର: {chr(65+right)}"
        nxt = current + 1
        c.execute("""UPDATE attempts SET q_index=?,score=?,correct=?,wrong=? WHERE user_id=?""",
                  (nxt,score,correct,wrong,u.id))
        if nxt >= 50:
            c.execute("UPDATE attempts SET finished=1 WHERE user_id=?", (u.id,))
    await query.edit_message_text(feedback)
    if nxt >= 50:
        await finish_message(query.message, u.id)
    else:
        await show_question(query.message, nxt)

async def finish_message(message, user_id):
    with db() as c:
        r = c.execute("SELECT score,correct,wrong,skipped,started FROM attempts WHERE user_id=?", (user_id,)).fetchone()
    score, correct, wrong, skipped, started = r
    accuracy = (correct / (correct+wrong+skipped) * 100) if correct+wrong+skipped else 0
    await message.reply_text(
        f"🏁 Test ସମାପ୍ତ!\n\nସ୍କୋର: {score:.2f}/50\nସଠିକ୍: {correct}\nଭୁଲ୍: {wrong}\nଛାଡ଼ିଥିବା: {skipped}\nAccuracy: {accuracy:.2f}%\n\n/leaderboard ଦେଖି Rank ଜାଣ।"
    )

async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    with db() as c:
        r = c.execute("SELECT score,correct,wrong,skipped,finished FROM attempts WHERE user_id=?", (u.id,)).fetchone()
    if not r:
        await update.message.reply_text("ପ୍ରଥମେ /start କରି Test ଆରମ୍ଭ କର।"); return
    score, correct, wrong, skipped, finished = r
    total = correct+wrong+skipped
    await update.message.reply_text(
        f"{'🏁 Test ସମାପ୍ତ' if finished else '📝 Test ଚାଲୁ ଅଛି'}\nScore: {score:.2f}/50\nCorrect: {correct} | Wrong: {wrong} | Skipped: {skipped}\nAccuracy: {(correct/total*100 if total else 0):.2f}%"
    )

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as c:
        rows = c.execute("""SELECT username,first_name,score,correct,wrong,skipped
          FROM attempts WHERE finished=1 ORDER BY score DESC, correct DESC, wrong ASC LIMIT 20""").fetchall()
    if not rows:
        await update.message.reply_text("ଏପର୍ଯ୍ୟନ୍ତ କେହି Test ସମାପ୍ତ କରିନାହାନ୍ତି।"); return
    lines = ["🏆 COMMON LEADERBOARD – TOP 20", ""]
    for i,(username,first,score,correct,wrong,skipped) in enumerate(rows,1):
        name = "@"+username if username else (first or "Student")
        total = correct+wrong+skipped
        acc = correct/total*100 if total else 0
        lines.append(f"{i}. {name} — {score:.2f} | {acc:.1f}%")
    await update.message.reply_text("\n".join(lines))

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start – Test ଆରମ୍ଭ\n/result – ନିଜ Result\n/leaderboard – Top 20 Rank")

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("result", result))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(begin, pattern="^begin$"))
    app.add_handler(CallbackQueryHandler(answer, pattern="^ans:"))
    app.run_polling()

if __name__ == "__main__":
    main()
