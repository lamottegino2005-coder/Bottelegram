import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN = "8706533462:AAGc-BHLCM-hec4q6apybNeOAtvYvu2wPnU"
ADMIN_ID = 7317807696

# ─── ÉTATS CONVERSATION ───────────────────────────────────────────────────────
ATTENTE_USER_ID  = 0
ATTENTE_MONTANT  = 1

ATTENTE_NOM_PRODUIT  = 10
ATTENTE_DESC_PRODUIT = 11
ATTENTE_PRIX_PRODUIT = 12

# ─── BASE DE DONNÉES ──────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id  INTEGER PRIMARY KEY,
            username TEXT,
            solde    REAL DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS produits (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nom         TEXT,
            description TEXT,
            prix        REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id  INTEGER,
            type     TEXT,
            montant  REAL,
            detail   TEXT,
            date     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_solde(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT solde FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0.0

def inscrire_user(user_id, username):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO users (user_id, username, solde) VALUES (?,?,0)",
        (user_id, username)
    )
    conn.commit()
    conn.close()

def ajouter_solde(user_id, montant):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET solde = solde + ? WHERE user_id=?", (montant, user_id))
    c.execute(
        "INSERT INTO transactions (user_id, type, montant, detail) VALUES (?,?,?,?)",
        (user_id, "recharge", montant, f"Recharge admin +{montant:.2f}€")
    )
    conn.commit()
    conn.close()

def debiter_solde(user_id, montant, detail):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET solde = solde - ? WHERE user_id=?", (montant, user_id))
    c.execute(
        "INSERT INTO transactions (user_id, type, montant, detail) VALUES (?,?,?,?)",
        (user_id, "achat", montant, detail)
    )
    conn.commit()
    conn.close()

def get_produits():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT id, nom, description, prix FROM produits")
    rows = c.fetchall()
    conn.close()
    return rows

def get_produit_by_id(produit_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT nom, description, prix FROM produits WHERE id=?", (produit_id,))
    row = c.fetchone()
    conn.close()
    return row

def ajouter_produit(nom, description, prix):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO produits (nom, description, prix) VALUES (?,?,?)",
        (nom, description, prix)
    )
    conn.commit()
    conn.close()

def supprimer_produit(produit_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("DELETE FROM produits WHERE id=?", (produit_id,))
    conn.commit()
    conn.close()

def get_historique(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute(
        "SELECT type, montant, detail, date FROM transactions "
        "WHERE user_id=? ORDER BY date DESC LIMIT 10",
        (user_id,)
    )
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_users():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, username, solde FROM users")
    rows = c.fetchall()
    conn.close()
    return rows

# ─── MENU PRINCIPAL ───────────────────────────────────────────────────────────
def menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 Boutique",   callback_data="boutique")],
        [InlineKeyboardButton("💰 Mon solde",  callback_data="solde")],
        [InlineKeyboardButton("📋 Historique", callback_data="historique")],
    ])

# ─── COMMANDES CLIENT ─────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    inscrire_user(user.id, user.username or user.first_name)
    solde = get_solde(user.id)
    await update.message.reply_text(
        f"👋 Bonjour {user.first_name} !\n\n"
        f"💰 Votre solde : *{solde:.2f} €*\n\n"
        "Que souhaitez-vous faire ?",
        reply_markup=menu_keyboard(),
        parse_mode="Markdown"
    )

async def cmd_solde(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    inscrire_user(user.id, user.username or user.first_name)
    solde = get_solde(user.id)
    await update.message.reply_text(
        f"💰 Votre solde : *{solde:.2f} €*",
        parse_mode="Markdown"
    )

# ─── CALLBACKS ────────────────────────────────────────────────────────────────
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    data  = query.data

    if data == "menu":
        solde = get_solde(user.id)
        await query.edit_message_text(
            f"💰 Votre solde : *{solde:.2f} €*\n\nQue souhaitez-vous faire ?",
            reply_markup=menu_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "solde":
        solde = get_solde(user.id)
        await query.edit_message_text(
            f"💰 Votre solde actuel : *{solde:.2f} €*\n\nContactez l'admin pour recharger.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data="menu")]]),
            parse_mode="Markdown"
        )

    elif data == "boutique":
        produits = get_produits()
        if not produits:
            await query.edit_message_text(
                "🛍 La boutique est vide pour le moment.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data="menu")]]),
            )
            return
        keyboard = [
            [InlineKeyboardButton(f"{p[1]} — {p[3]:.2f}€", callback_data=f"acheter_{p[0]}")]
            for p in produits
        ]
        keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="menu")])
        await query.edit_message_text(
            "🛍 *Boutique* — Choisissez un article :",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data.startswith("acheter_"):
        produit_id = int(data.split("_")[1])
        p = get_produit_by_id(produit_id)
        if not p:
            await query.edit_message_text("❌ Produit introuvable.")
            return
        solde = get_solde(user.id)
        if solde < p[2]:
            await query.edit_message_text(
                f"❌ Solde insuffisant.\n\n"
                f"💰 Votre solde : *{solde:.2f}€*\n"
                f"💵 Prix : *{p[2]:.2f}€*\n\n"
                f"Contactez l'admin pour recharger.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data="boutique")]]),
                parse_mode="Markdown"
            )
            return
        debiter_solde(user.id, p[2], f"Achat : {p[0]}")
        nouveau_solde = get_solde(user.id)
        await query.edit_message_text(
            f"✅ Achat confirmé !\n\n"
            f"🛍 *{p[0]}*\n"
            f"📝 {p[1]}\n\n"
            f"💰 Solde restant : *{nouveau_solde:.2f}€*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="menu")]]),
            parse_mode="Markdown"
        )

    elif data == "historique":
        historique = get_historique(user.id)
        if not historique:
            await query.edit_message_text(
                "📋 Aucune transaction pour le moment.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data="menu")]]),
            )
            return
        texte = "📋 *Vos 10 dernières transactions :*\n\n"
        for t in historique:
            emoji = "➕" if t[0] == "recharge" else "🛍"
            texte += f"{emoji} {t[2]} — *{t[1]:.2f}€* — {str(t[3])[:10]}\n"
        await query.edit_message_text(
            texte,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data="menu")]]),
            parse_mode="Markdown"
        )

# ─── ADMIN : RECHARGER ────────────────────────────────────────────────────────
async def admin_recharge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Accès refusé.")
        return ConversationHandler.END
    await update.message.reply_text(
        "👤 Entrez le *Telegram ID* du client à recharger :",
        parse_mode="Markdown"
    )
    return ATTENTE_USER_ID

async def recharge_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(update.message.text.strip())
        context.user_data["recharge_uid"] = uid
        await update.message.reply_text(
            "💵 Entrez le *montant* à ajouter (ex: 20) :",
            parse_mode="Markdown"
        )
        return ATTENTE_MONTANT
    except ValueError:
        await update.message.reply_text("❌ ID invalide. Réessayez avec /recharge")
        return ConversationHandler.END

async def recharge_montant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        montant = float(update.message.text.strip().replace(",", "."))
        uid = context.user_data["recharge_uid"]
        inscrire_user(uid, "inconnu")
        ajouter_solde(uid, montant)
        nouveau_solde = get_solde(uid)
        await update.message.reply_text(
            f"✅ *{montant:.2f}€* ajoutés au client `{uid}`\n"
            f"💰 Nouveau solde : *{nouveau_solde:.2f}€*",
            parse_mode="Markdown"
        )
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=(
                    f"💰 Votre compte a été rechargé de *{montant:.2f}€* !\n\n"
                    f"💳 Nouveau solde : *{nouveau_solde:.2f}€*\n\n"
                    f"Tapez /start pour accéder à la boutique."
                ),
                parse_mode="Markdown"
            )
        except Exception:
            pass
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Montant invalide. Entrez un nombre (ex: 20.50)")
        return ATTENTE_MONTANT

# ─── ADMIN : AJOUTER PRODUIT ──────────────────────────────────────────────────
async def admin_add_produit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Accès refusé.")
        return ConversationHandler.END
    await update.message.reply_text("📦 Entrez le *nom* du produit :", parse_mode="Markdown")
    return ATTENTE_NOM_PRODUIT

async def add_nom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["prod_nom"] = update.message.text.strip()
    await update.message.reply_text("📝 Entrez la *description* du produit :", parse_mode="Markdown")
    return ATTENTE_DESC_PRODUIT

async def add_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["prod_desc"] = update.message.text.strip()
    await update.message.reply_text("💵 Entrez le *prix* du produit (ex: 9.99) :", parse_mode="Markdown")
    return ATTENTE_PRIX_PRODUIT

async def add_prix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        prix = float(update.message.text.strip().replace(",", "."))
        nom  = context.user_data["prod_nom"]
        desc = context.user_data["prod_desc"]
        ajouter_produit(nom, desc, prix)
        await update.message.reply_text(
            f"✅ Produit *{nom}* ajouté à *{prix:.2f}€* !",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Prix invalide. Entrez un nombre (ex: 9.99)")
        return ATTENTE_PRIX_PRODUIT

# ─── ADMIN : SUPPRIMER PRODUIT ────────────────────────────────────────────────
async def admin_list_produits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Accès refusé.")
        return
    produits = get_produits()
    if not produits:
        await update.message.reply_text("🛍 Aucun produit enregistré.")
        return
    texte = "🗑 *Produits disponibles :*\n\n"
    for p in produits:
        texte += f"ID `{p[0]}` — {p[1]} — {p[3]:.2f}€\n"
    texte += "\nPour supprimer : `/delproduit ID`"
    await update.message.reply_text(texte, parse_mode="Markdown")

async def admin_del_produit_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Accès refusé.")
        return
    if not context.args:
        await update.message.reply_text("❌ Usage : /delproduit ID")
        return
    try:
        pid = int(context.args[0])
        supprimer_produit(pid)
        await update.message.reply_text(f"✅ Produit `{pid}` supprimé.", parse_mode="Markdown")
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Usage : /delproduit ID")

# ─── ADMIN : LISTE CLIENTS ────────────────────────────────────────────────────
async def admin_clients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Accès refusé.")
        return
    users = get_all_users()
    if not users:
        await update.message.reply_text("Aucun client enregistré.")
        return
    texte = "👥 *Liste des clients :*\n\n"
    for u in users:
        texte += f"🆔 `{u[0]}` — @{u[1]} — 💰 {u[2]:.2f}€\n"
    await update.message.reply_text(texte, parse_mode="Markdown")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    init_db()
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )

    app = Application.builder().token(TOKEN).build()

    # ConversationHandler recharge (enregistré EN PREMIER)
    recharge_conv = ConversationHandler(
        entry_points=[CommandHandler("recharge", admin_recharge)],
        states={
            ATTENTE_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, recharge_user_id)],
            ATTENTE_MONTANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, recharge_montant)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    app.add_handler(recharge_conv)

    # ConversationHandler ajout produit
    add_prod_conv = ConversationHandler(
        entry_points=[CommandHandler("addproduit", admin_add_produit)],
        states={
            ATTENTE_NOM_PRODUIT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_nom)],
            ATTENTE_DESC_PRODUIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_desc)],
            ATTENTE_PRIX_PRODUIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_prix)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    app.add_handler(add_prod_conv)

    # Commandes simples
    app.add_handler(CommandHandler("start",      start))
    app.add_handler(CommandHandler("solde",      cmd_solde))
    app.add_handler(CommandHandler("produits",   admin_list_produits))
    app.add_handler(CommandHandler("delproduit", admin_del_produit_id))
    app.add_handler(CommandHandler("clients",    admin_clients))

    # Callbacks boutons (EN DERNIER)
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("✅ Bot démarré !")
    app.run_polling()

if __name__ == "__main__":
    main()
