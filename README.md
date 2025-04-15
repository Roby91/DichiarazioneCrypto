# 🧾 DichiarazioneCrypto

**DichiarazioneCrypto** è un progetto open source che ha l'obiettivo di **agevolare la compilazione delle dichiarazioni fiscali italiane** (Modello 730, ISEE, ecc.) a chi possiede o ha effettuato operazioni in criptovalute.  

Questo strumento è capace di elaborare gli **estratti conto degli exchange** - *per adesso è supportato solo Coinbase* - in modo da fornire alcuni dei dati da dichiarare nei documenti fiscali (plusvalenze, giacenze medie e altri dati richiesti per ISEE e Modello 730).



---

## 🎯 Obiettivi principali

- 🧮 **Calcolo automatico** di plusvalenze, giacenze medie e altri dati richiesti per ISEE e Modello 730.

- 📁 **Gestione ordinata per anno fiscale** secondo le regole vigenti (es. `/fiscal_years/2025/`, `/fiscal_years/2026/`, ecc).

- 🐳 **Utilizzo tramite Docker**, per facilitare l'esecuzione su qualsiasi sistema senza configurazioni complicate.

- 🖥️ **Interfaccia grafica (GUI)** prevista in una fase successiva, eseguibile direttamente su Windows, macOS e Linux.

- 📊 **Prezzi storici integrati** per BTC/EUR, ETH/EUR (altre crypto saranno aggiunte grazie alla community).

  

---

## 📦 Esempio d'uso (da terminale)

```bash
docker run --rm -v $(pwd):/data dichiarazionecrypto \
  --anno 2025 \
  --file /data/movimenti_coinbase.csv \
  --output /data/report_fiscale_2025.pdf
```

⚠️ In sviluppo: sintassi e funzionalità potrebbero cambiare. Segui il progetto per gli aggiornamenti!



------

## 🚧 Stato del progetto

Attualmente in fase **early development**.
 Le funzionalità base per l'anno fiscale **2025** sono in fase di definizione.

Se vuoi partecipare:

- Dai un'occhiata alla [roadmap](#roadmap)

- Leggi la [guida per i contributor](CONTRIBUTING.md) (in arrivo)

- Apri una [issue](https://github.com/Roby91/DichiarazioneCrypto/issues) o proponi una [pull request](https://github.com/Roby91/DichiarazioneCrypto/pulls)

  

------

## 🤝 Contribuire

**Ogni contributo è benvenuto!**
 Puoi aiutare anche se non sei uno sviluppatore:

- Segnalando bug o anomalie fiscali
- Fornendo fonti ufficiali sulle normative
- Condividendo test-case reali anonimizzati
- Aggiungendo supporto per altre criptovalute

Il progetto è e **rimarrà gratuito e open source**, per aiutare chiunque abbia bisogno di orientarsi nella fiscalità crypto.



------

## 📚 Roadmap

- ✅ Struttura base del progetto per anno fiscale

- ⏳ Parsing CSV Coinbase

- ⏳ Calcolo giacenze e plusvalenze (2025)

- ⏳ Output PDF per supporto 730/ISEE

- ⏳ Dockerfile stabile

- 🕐 GUI multipiattaforma (fase successiva)

- 🕐 Supporto per nuovi exchange / criptovalute (tramite community)

  

------

## 🛠️ Tech stack

- Python 3.11+

- Pandas / NumPy

- Docker

- (in futuro) PySide / Tauri / Electron per GUI

  

------

## 📄 Licenza

Questo progetto è distribuito sotto licenza **GPLv3**.
Usalo, modificalo, miglioralo, ma sempre nel rispetto della licenza. 🙏



------

## 🌐 Contatti e aggiornamenti

Segui il progetto su [GitHub](https://github.com/Roby91/DichiarazioneCrypto)
Per qualsiasi domanda o proposta, apri una issue o contattami tramite le discussioni del repo.