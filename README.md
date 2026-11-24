# Anti-Fragilità e Teoria dei Costruttori: Un'Indagine Computazionale

Questo repository contiene il codice e i risultati di un esperimento computazionale volto a esplorare l'intersezione tra la **Teoria del Cigno Nero** (Nassim Taleb), la **Teoria dei Costruttori** (David Deutsch e Chiara Marletto) e il concetto di **Possibile Adiacente** (Stuart Kauffman). 

L'obiettivo è indagare se la "conoscenza potenziale" (Knowledge Potential, KP) accumulata da un sistema in condizioni favorevoli possa fungere da riserva strutturale (resilienza) quando il sistema affronta perturbazioni imprevedibili.

## Metodologia

L'esperimento utilizza il framework **cECT-T (Computable Embodied Constructor Theory)** v4.2. Sono stati simulati due agenti (costruttori) con storie di apprendimento diverse:
- **Agente A**: addestrato in un ambiente "mite" (nominale), dove accumula un alto livello di KP.
- **Agente B**: addestrato in un ambiente "severo" (ostile), dove il KP cresce meno.

Successivamente, entrambi gli agenti sono stati sottoposti a una serie di test di stress e recupero.

## Risultati Chiave

I dati raccolti (file JSON in questo repository) dimostrano che **il KP non è un predittore del successo nel completamento del compito, ma è un predittore della resilienza strutturale e della capacità di recupero**.

### 1. Resilienza allo Shock Severo
Sotto uno shock estremo, entrambi gli agenti hanno fallito il compito (success rate = 0.0). Tuttavia, l'Agente A (alto KP) ha mostrato una capacità di assorbimento dello shock drasticamente superiore in termini di integrità e vitalità, mantenendo un "cuscinetto" strutturale che l'Agente B non possedeva.

### 2. Resilienza allo Shock Moderato
Sotto stress moderato, entrambi gli agenti hanno continuato a fallire il compito. Ma l'Agente A ha mostrato una capacità di assorbimento dello shock superiore:
- **Agente A**: Integrità finale `0.84`, Vitalità `0.68`, KP in crescita.
- **Agente B**: Integrità finale `0.65`, Vitalità `0.59`.

### 3. Recupero Post-Shock
Dopo uno shock severo e il successivo ritorno alla normalità, l'Agente A ha mostrato una "cicatrice" molto più lieve e una capacità di recupero superiore:
- **Agente A**: Integrità post-shock `0.72` → recupero a `0.92`.
- **Agente B**: Integrità post-shock `0.52` → recupero a `0.72`.

### 4. Recupero Atomico Post-Shock (Esperimento Finale)
Per testare se l'alto KP conferisce non solo una protezione strutturale, ma anche una *capacità operativa residua*, abbiamo condotto un ultimo esperimento. Dopo lo shock severo, abbiamo riportato l'ambiente in condizioni nominali e abbiamo assegnato agli agenti un compito atomico (la singola trasformazione `warm`), invece della sequenza completa `warm_then_stabilize`. 

**Risultati:**
- **Agente A (Alto KP):** Integrità post-shock `0.72` → recupero a `0.92`. Vitalità finale `0.71`. KP in crescita da `3.19` a `4.35`.
- **Agente B (Basso KP):** Integrità post-shock `0.52` → recupero a `0.72`. Vitalità finale `0.62`. KP in crescita da `1.71` a `2.88`.

**Interpretazione:**
Entrambi gli agenti hanno fallito il compito atomico (`success_rate = 0.0`). Questo conferma che, nel framework cECT-T, un costruttore che subisce uno shock profondo perde la capacità di eseguire compiti con successo anche quando l'ambiente torna favorevole. Tuttavia, **la vitalità e l'integrità strutturale dell'Agente A rimangono significativamente superiori**. 

Questo dimostra che il KP non è un predittore della performance operativa immediata (il successo nel compito), ma un **predittore della resilienza strutturale e della capacità di persistenza**. L'Agente A, pur non riuscendo a completare il compito, mantiene una "salute" sistemica molto più alta, un "pavimento" strutturale che gli permette di continuare ad accumulare conoscenza potenziale e di non collassare.

## Interpretazione Teorica Finale

Il trittico sperimentale (shock severo, shock moderato, recupero atomico) supporta l'idea che la conoscenza potenziale (KP) agisca come una **riserva anti-fragile**. In linea con la Teoria dei Costruttori (Deutsch/Marletto), il KP non serve a prevedere o a garantire il successo in un compito specifico, ma garantisce la **persistenza del costruttore** e la sua capacità di mantenere l'integrità di fronte a perturbazioni non specificate. In linea con Taleb, il sistema non "vince" contro il cigno nero, ma sopravvive ad esso con una struttura più solida. L'alto KP sembra inoltre espandere il "Possibile Adiacente" (Kauffman), permettendo al sistema di esplorare e ripristinare la propria funzionalità più velocemente.

## Struttura del Repository

- `cect_t_canonical_v4_2_clean_publication_ready/`: Il framework cECT-T originale.
- `esperimento_perturbazione.py`: Script per lo shock severo iniziale.
- `esperimento_moderato.py`: Script per lo shock moderato.
- `esperimento_recupero.py`: Script per il test di recupero post-shock.
- `esperimento_passo_avanti.py`: Script per il test del compito atomico post-shock.
- `*.json`: I risultati numerici grezzi delle simulazioni.

## Come Riprodurre gli Esperimenti

1. Clona questo repository.
2. Assicurati di avere `numpy` installato (`pip install numpy`).
3. Esegui gli script:
   ```bash
   python esperimento_perturbazione.py
   python esperimento_moderato.py
   python esperimento_recupero.py
   python esperimento_passo_avanti.py