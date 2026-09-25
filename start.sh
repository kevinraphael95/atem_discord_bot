# ================================================================================
# 📌 start.sh (Atem)
# Objectif : Lancer le bot Atem, détaché du terminal
# Catégorie : Système
# Accès : Admin / Local
# Cooldown : Aucun
# ================================================================================

# Se placer dans le dossier du script (racine du bot)
cd "$(dirname "$0")"

echo "════════════════════════════════════════"
echo "  ATEM BOT — DÉMARRAGE"
echo "════════════════════════════════════════"

# ================================================================================
# 🤖 Lancement du Bot Discord
# ================================================================================
# setsid + nohup détachent le bot de ce terminal : fermer Termux (ou cette
# session bash) ne tue plus le bot. Les logs partent dans bot.log au lieu de
# s'afficher directement ici — utilise `tail -f bot.log` pour les voir en
# direct depuis n'importe quelle session Termux.
echo "🤖 Lancement du bot (détaché, logs dans bot.log)..."
setsid nohup python bot.py > bot.log 2>&1 < /dev/null &
disown
BOT_PID=$!

echo ""
echo "✅ Bot lancé en arrière-plan (PID $BOT_PID)"
echo "📄 Logs : tail -f bot.log"
echo ""
