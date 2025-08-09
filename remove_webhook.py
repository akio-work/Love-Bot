import requests

TOKEN = "8232680735:AAG-GFL8ZOUla-OwP-0D5bDhnFpNaH6e-pU"
url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"

response = requests.get(url)
if response.status_code == 200:
    print("Webhook успішно видалено!")
else:
    print(f"Щось пішло не так: {response.status_code} {response.text}")
