# Ontology & Alias Learning

Das System verfügt über Mechanismen, um automatisch Variationen von Namen (Aliase) zu lernen und diese im Wissensgraphen zu konsolidieren.

## Alias-Tabelle
In der `MetadataStore` existiert eine `aliases` Tabelle, die verschiedene Namen auf einen kanonischen (einheitlichen) Namen mappt. Dies verhindert Duplikate im Wissensgraphen (z.B. "KI" und "Künstliche Intelligenz" als zwei separate Knoten).

## Ontology Learner
Das Modul `mcp_university/knowledge_graph/ontology_learner.py` automatisiert diesen Prozess:

1.  **E-Mail-Header Analyse:** Es extrahiert Name-E-Mail-Paare aus den Headern verarbeiteter E-Mails. Dies hilft dabei, Personen eindeutig zu identifizieren, auch wenn sie unterschiedliche Anzeigenamen verwenden.  
2.  **LLM-basierte Konsolidierung:** Bestehende Knoten im Wissensgraph werden durch ein LLM analysiert, um semantische Variationen zu finden (z.B. Abkürzungen von Modulen).  
3.  **Kanonisierung:** Bevor ein neuer Knoten in den Wissensgraph eingefügt wird, prüft das System, ob für diesen Namen ein kanonischer Alias existiert und verwendet diesen bevorzugt.  

## Kanten-Prioritäten
In der `ontology.yaml` können Prioritäten für verschiedene Beziehungstypen definiert werden. Wenn die `KnowledgeGraphEngine` eine neue Beziehung zwischen zwei Knoten findet, die bereits verknüpft sind, entscheidet die Priorität, ob die alte Beziehung ersetzt wird. Dies stellt sicher, dass qualitativ hochwertigere Informationen (z.B. aus MOCOGI) weniger präzise Informationen (z.B. aus einer E-Mail-Extraktion) überschreiben.
