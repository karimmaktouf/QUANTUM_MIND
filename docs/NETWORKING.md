# Rétablir la sortie réseau/DNS vers le leaderboard LMSYS

La fonctionnalité de rafraîchissement MT-Bench dépend d'un appel HTTPS vers `https://chat.lmsys.org/api/leaderboard`. Si cette URL n'est plus joignable, les données restent figées sur les snapshots organisés. Ce guide décrit comment diagnostiquer et rétablir la résolution DNS et la sortie HTTPS depuis Windows.

## 1. Symptômes et vérifications rapides
1. **Tester la résolution et le port 443**
   ```powershell
   Test-NetConnection -ComputerName chat.lmsys.org -Port 443
   ```
   - `Name resolution failed` ➜ DNS ne connaît pas le domaine.
   - `TcpTestSucceeded : False` avec adresse IP ➜ pare-feu ou proxy bloque la sortie 443.

2. **Inspecter le cache DNS local**
   ```powershell
   ipconfig /displaydns | Select-String "chat.lmsys.org"
   ```

3. **Vérifier depuis Python (mêmes dépendances que l'app)**
   ```powershell
   C:/Users/Admin/AppData/Local/Programs/Python/Python313/python.exe scripts/check_leaderboard.py
   ```

## 2. Rétablir la résolution DNS
1. **Purger le cache DNS local**
   ```powershell
   ipconfig /flushdns
   ```

2. **Forcer des résolveurs publics (si autorisé)** *(commande à exécuter dans une console PowerShell ouverte « en tant qu'administrateur »)*
   ```powershell
   # Adapter "Ethernet"/"Wi-Fi" au nom de l'interface active
   Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses 1.1.1.1,8.8.8.8
   ```
   > Revenir à l'automatique ensuite : `Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ResetServerAddresses`

3. **Contrôler le fichier hosts** (`C:\Windows\System32\drivers\etc\hosts`)
   - Supprimer toute ligne obsolète contenant `lmsys.org`.
   - Ajouter une entrée **uniquement** si vous connaissez l'IP officielle (exemple) :
     ```
     172.67.214.147   chat.lmsys.org
     ```
     > Vérifier l'IP auprès d'une source fiable (`nslookup chat.lmsys.org 1.1.1.1`).

4. **DNS filtré / proxy**
   - Si votre entreprise impose un proxy, configurez les variables d'environnement utilisées par Python :
     ```powershell
     setx HTTPS_PROXY "http://proxy.local:8080"
     setx HTTP_PROXY  "http://proxy.local:8080"
     ```

## 3. Autoriser la sortie HTTPS
1. **Contrôler Windows Defender Firewall**
   ```powershell
   Get-NetFirewallRule -Direction Outbound -Action Block | Select-String "Python" | Select-Object -First 10
   ```

2. **Créer une règle d'autorisation ciblée** (si un blocage explicite est présent)
   ```powershell
   New-NetFirewallRule -DisplayName "Allow LMSYS Leaderboard" \ 
     -Direction Outbound -Action Allow -Protocol TCP -RemotePort 443 \ 
     -Program "C:\Users\Admin\AppData\Local\Programs\Python\Python313\python.exe"
   ```

3. **Vérifier les solutions tierces** (antivirus, ZTNA, VPN) et ajouter `chat.lmsys.org` / `*.lmsys.org` à la liste verte.

## 4. Validation après remédiation
1. `Resolve-DnsName chat.lmsys.org`
2. `Test-NetConnection chat.lmsys.org -Port 443`
3. `python scripts/check_leaderboard.py` (cf. section suivante)
4. Dans l'application : bouton **Refresh MT-Bench** ou attendre le scheduler ➜ le compteur devrait remonter >0.

## 5. Astuces supplémentaires
- Autorisez également `https://huggingface.co` et `https://export.arxiv.org` si vous utilisez les autres outils intégrés.
- Exportez `LMSYS_API_URL` pour cibler un miroir interne temporaire :
  ```powershell
  setx LMSYS_API_URL "https://mon-proxy-interne.local/leaderboard"
  ```
  L'application reprendra automatiquement cette URL au prochain redémarrage (cf. `app/agent.py`).

Une fois la résolution rétablie, aucun autre changement n'est nécessaire : le cache MT-Bench et le scheduler rechargeront les scores automatiquement.
