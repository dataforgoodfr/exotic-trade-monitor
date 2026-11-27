# Infra as code

le dossier infra contient la description de l'infrastructure necessaire au projet.

## Creation

La description à été initialisée par un import de l'infrastructure créee via la console Clever Cloud. Les commandes suivantes ont permi de générer une bonne partie des fichiers :

Récupération des composants existants

```sh
tofu init

clever features enable terraform
clever terraform generate --org "Code animal x D4G" > imports.tf
```

Génération des resources

```sh
tofu plan -generate-config-out=generated.tf
```

## Mise à jour

La mise à jour doit passer par des étapes successives :

- Mise à jour de l'état souhaité dans les fichiers TF
- `tofu validate` pour vérifier que les fichiers sont valides
- `tofu plan -out=xxx.tfplan` pour sortir le plan d'application de l'état souhaité sur Clever cloud (lister les ajouts / changes / suppressions qui s'appliqueront si le plan est exécuté)
- `tofu apply xxx.tfplan` pour executer le plan

Lors de la création du plan, les variables qui portent les secrets doivent etre fournies (on ne peux pas les laisser en clair dans la configuration).

Utilisez `tofu fmt` pour formatter les fichiers de declaration tf avant un commit sur le repo.

## Automatisation

Pour le moment le provionning de l'infrastructure ne fait pas l'objet d'une automatisation via GitHub actions. Ca peut venir. A ce moment là les secrets seront enregistrés dans le repo Github et le workflow portera les etapes de verifications successives, le plan et l'apply après approbation du plan.

## Doc

[Documentation Clever Cloud](https://www.clever.cloud/developers/doc/tools/terraform/)
