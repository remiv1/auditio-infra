// Script page d'attente - polling du statut
let wakeRequested = false;
let checkCount = 0;

async function checkStatus() {
    checkCount++;
    
    try {
        const response = await fetch(`/api/status/${DOMAIN_NAME}`);
        const data = await response.json();

        // Mise à jour des statuts visuels
        updateStatus('status-server', data.server_online);
        updateStatus('status-service', data.service_ready);

        // Afficher les infos de politique
        updatePolicyInfo(data.policy);

        // Si le serveur n'est pas en ligne et WoL pas encore envoyé
        if (!data.server_online && !wakeRequested) {
            wakeRequested = true;
            await fetch(`/api/wake/${DOMAIN_NAME}`, { method: 'POST' });
        }

        // Si tout est prêt, rediriger
        if (data.ready && data.redirect_url) {
            // Signaler l'activité avant de rediriger
            await fetch(`/api/activity/${DOMAIN_NAME}`, { method: 'POST' });
            window.location.href = data.redirect_url;
        }
    } catch (error) {
        console.error('Erreur lors de la vérification:', error);
    }
}

function updateStatus(elementId, isReady) {
    const el = document.getElementById(elementId);
    if (!el) return;
    
    if (isReady) {
        el.classList.remove('pending');
        el.classList.add('done');
        el.querySelector('.icon').textContent = '✅';
    } else {
        el.classList.add('pending');
        el.querySelector('.icon').textContent = '⏳';
    }
}

function updatePolicyInfo(policy) {
    const el = document.getElementById('policy-info');
    if (!el || !policy) return;

    let message = '';
    switch (policy.reason) {
        case 'within_schedule':
            message = '📅 Dans les horaires programmés';
            break;
        case 'outside_schedule':
            message = '🌙 Hors horaires - réveil à la demande';
            break;
        case 'recent_activity':
            message = '⚡ Serveur actif';
            break;
        case 'idle_timeout':
            message = '💤 Serveur en veille - réveil en cours...';
            break;
        case 'always_on':
            message = '🔋 Serveur permanent';
            break;
    }
    
    el.textContent = message;
}

// Vérification initiale
checkStatus();

// Polling selon l'intervalle configuré
setInterval(checkStatus, POLLING_INTERVAL);
