async function api(url, method="GET", body=null) {
    const options = {
        method,
        headers: { "Content-Type": "application/json" },
        credentials: "include"
    };

    if (body) options.body = JSON.stringify(body);

    const res = await fetch(url, options);
    return res.json();
}

function logout() {
    fetch("/api/admin/logout", { method: "POST", credentials: "include" })
        .then(() => window.location.href = "/");
}
