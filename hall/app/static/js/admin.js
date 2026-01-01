async function reloadConfig() {
    const response = await fetch('/api/reload', { method: 'POST' });
    const data = await response.json();
    alert(data.message);
    if (data.success) location.reload();
}