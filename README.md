# Anti-Fragilità e Teoria dei Costruttori: Un'Indagine Computazionale

Questo repository contiene il codice e i risultati di un esperimento computazionale volto a esplorare l'intersezione tra la **Teoria del Cigno Nero** (Nassim Taleb), la **Teoria dei Costruttori** (David Deutsch e Chiara Marletto) e il concetto di **Possibile Adiacente** (Stuart Kauffman). 

L'obiettivo è indagare se la "conoscenza potenziale" (Knowledge Potential, KP) accumulata da un sistema in condizioni favorevoli possa fungere da riserva strutturale (resilienza) quando il sistema affronta perturbazioni imprevedibili.

## Metodologia

L'esperimento utilizza il framework **cECT-T (Computable Embodied Constructor Theory)** v4.2. Sono stati simulati due agenti (costruttori) con storie di apprendimento diverse:
- **Agente A**: addestrato in un ambiente "mite" (nominale), dove accumula un alto livello di KP.
- **Agente B**: addestrato in un ambiente "severo" (ostile), dove il KP cresce meno.

Successivamente, entrambi gli agenti sono stati sottoposti a tre fasi di test:
1. **Shock Severo**: perturbazione estrema che rende il compito fisicamente impossibile.
2. **Shock Moderato**: perturbazione che mantiene il compito possibile ma altamente stressante.
3. **Recupero**: ritorno a condizioni ambientali normali dopo uno shock severo.

## Risultati Chiave

I dati raccolti (file JSON in questo repository) dimostrano che **il KP non è un predittore del successo nel completamento del compito, ma è un predittore della resilienza strutturale e della capacità di recupero**.

### 1. Resilienza allo Shock Moderato
Sotto stress moderato, entrambi gli agenti hanno fallito il compito (success rate = 0.0). Tuttavia, l'Agente A (alto KP) ha mostrato una capacità di assorbimento dello shock drasticamente superiore:
- **Agente A**: Integrità finale `0.84`, Vitalità `0.68`, KP in crescita.
- **Agente B**: Integrità finale `0.65`, Vitalità `0.59`.

### 2. Recupero Post-Shock
Dopo uno shock severo e il successivo ritorno alla normalità, l'Agente A ha mostrato una "cicatrice" molto più lieve e una capacità di recupero superiore:
- **Agente A**: Integrità post-shock `0.72` → recupero a `0.92`.
- **Agente B**: Integrità post-shock `0.52` → recupero a `0.72`.

## Interpretazione Teorica

I risultati supportano l'idea di Taleb secondo cui l'anti-fragilità non è la capacità di prevedere o evitare il Cigno Nero, ma la capacità di **assorbire lo shock e rimanere strutturalmente vitali**. 

In termini di Teoria dei Costruttori (Deutsch/Marletto), il KP agisce come un'informazione fisica con una "resilienza distintiva": non garantisce il successo operativo immediato, ma garantisce la persistenza del costruttore. Inoltre, l'alto KP sembra espandere il "Possibile Adiacente" (Kauffman) del sistema, permettendogli di esplorare e ripristinare la propria funzionalità più velocemente una volta che l'ambiente torna favorevole.

## Struttura del Repository

- `cect_t_canonical_v4_2_clean_publication_ready/`: Il framework cECT-T originale.
- `esperimento_perturbazione.py`: Script per lo shock severo iniziale.
- `esperimento_moderato.py`: Script per lo shock moderato.
- `esperimento_recupero.py`: Script per il test di recupero post-shock.
- `*.json`: I risultati numerici grezzi delle simulazioni.

## Come Riprodurre gli Esperimenti

1. Clona questo repository.
2. Assicurati di avere `numpy` installato (`pip install numpy`).
3. Esegui gli script:
   ```bash
   python esperimento_perturbazione.py
   python esperimento_moderato.py
   python esperimento_recupero.py