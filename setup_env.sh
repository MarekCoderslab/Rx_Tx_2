

# setup_env.sh — inicializace vývojového prostředí

echo "🔧 Vytvářím virtuální prostředí..."
python3 -m venv venv

echo "✅ Aktivuji prostředí..."
source venv/bin/activate

echo "📦 Aktualizuji pip..."
pip install --upgrade pip

if [ -f requirements.txt ]; then
    echo "📚 Instaluji balíčky z requirements.txt..."
    pip install -r requirements.txt
else
    echo "⚠️ Soubor requirements.txt nebyl nalezen."
fi

echo "🧠 Nastavuji VS Code interpreter..."
mkdir -p .vscode
echo '{
  "python.defaultInterpreterPath": "venv/bin/python"
}' > .vscode/settings.json

echo "🎉 Hotovo! Prostředí je připraveno."
