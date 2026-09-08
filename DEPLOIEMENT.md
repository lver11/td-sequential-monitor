# Déployer l'application

## Render

1. Crée un compte sur [Render](https://render.com/).
2. Crée un dépôt GitHub et ajoute le contenu du dossier `outputs`.
3. Dans Render, choisis **New > Blueprint**.
4. Sélectionne ton dépôt GitHub et le fichier `render.yaml`.
5. Lance le déploiement.

Render fournira une URL publique du type `https://td-sequential-scanner.onrender.com`.
L'application et son relais Yahoo Finance fonctionneront sur cette même URL.

Le service utilise le plan gratuit de Render si disponible. Il peut s'endormir après une période
d'inactivité et prendre quelques secondes à redémarrer.
