import time
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright

app = FastAPI()

# Permette al tuo sito GitHub di fare richieste a questa API senza blocchi CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

URL_GOOGLE_SCRIPT = "https://script.google.com/macros/s/AKfycbx7BIgETqlz8bq20eEwRSUHW1xHqqV5g7jqfsZWz0BkVdZj23idU8OAYr1aAFzg68cL/exec"

def scrape_jartex(username: str):
    modalita = "bedwars"
    url = f"https://stats.jartexnetwork.com/player/{username}/{modalita}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()
        
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(5)  # Attesa caricamento dati
            
            righe = page.locator("table tbody tr")
            num_righe = righe.count()
            
            if num_righe == 0:
                return None
                
            raw_data = {}
            voci_da_escludere = ["games played", "bow kills", "arrows shot", "arrows hit", "december wins", "melee kills", "void kills"]
            
            for i in range(num_righe):
                riga = righe.nth(i)
                celle = riga.locator("td")
                if celle.count() >= 2:
                    if celle.count() == 3:
                        nome_stat = celle.nth(1).inner_text().strip().lower()
                        valore_stat = celle.nth(2).inner_text().strip()
                    else:
                        nome_stat = celle.nth(0).inner_text().strip().lower()
                        valore_stat = celle.nth(1).inner_text().strip()
                    
                    if nome_stat in voci_da_escludere:
                        continue
                    
                    valore_pulito = valore_stat.replace(",", "")
                    try:
                        raw_data[nome_stat] = int(valore_pulito)
                    except ValueError:
                        raw_data[nome_stat] = valore_stat

            highest_ws = 0
            for chiave, valore in raw_data.items():
                if "winstreak" in chiave:
                    highest_ws = valore
                    break

            wins = raw_data.get("wins", 0)
            losses = raw_data.get("losses", 0)
            deaths = raw_data.get("deaths", 0)
            kills = raw_data.get("kills", 0) 
            final_kills = raw_data.get("final kills", 0)
            final_deaths = raw_data.get("final deaths", 0)
            beds_destroyed = raw_data.get("beds destroyed", 0)
            
            wlr = round(wins / losses, 2) if losses > 0 else float(wins)
            kdr = round(kills / deaths, 2) if deaths > 0 else float(kills)
            fkdr = round(final_kills / final_deaths, 2) if final_deaths > 0 else float(final_kills)
            
            payload = {
                "nickname": username.upper(),
                "kills": kills,
                "final_kills": final_kills,
                "highest_ws": highest_ws,
                "beds_destroyed": beds_destroyed,
                "losses": losses,
                "deaths": deaths,
                "wins": wins,
                "wlr": wlr,
                "kdr": kdr,
                "fkdr": fkdr
            }
            
            try:
                requests.post(URL_GOOGLE_SCRIPT, json=payload, timeout=5)
            except Exception:
                pass
                
            return payload
        except Exception as e:
            print(f"Errore Scraper: {e}")
            return None
        finally:
            context.close()
            browser.close()

@app.get("/api/stats/{username}")
def get_stats(username: str):
    dati = scrape_jartex(username.strip())
    if not dati:
        raise HTTPException(status_code=404, detail="Giocatore non trovato o errore nel recupero dati.")
    return {"errore": False, "giocatore": dati["nickname"], "stats": dati}
