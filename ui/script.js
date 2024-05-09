
document.addEventListener("DOMContentLoaded", function() {
    const openAccountForm = document.querySelector("#openAccountForm");
    const openCreditCardForm = document.querySelector("#openCreditCardForm");
    const openAccountResult = document.querySelector("#openAccountResult");
    const openCreditCardResult = document.querySelector("#openCreditCardResult");

    openAccountForm.addEventListener("submit", function(event) {
        event.preventDefault();
        const formData = new FormData(this);
        fetch(this.getAttribute("action"), {
            method: "POST",
            body: formData
        })
        .then(response => response.text())
        .then(data => {
            openAccountResult.textContent = data;
        })
        .catch(error => {
            console.error("Error:", error);
        });
    });

    openCreditCardForm.addEventListener("submit", function(event) {
        event.preventDefault();
        const formData = new FormData(this);
        fetch(this.getAttribute("action"), {
            method: "POST",
            body: formData
        })
        .then(response => response.text())
        .then(data => {
            openCreditCardResult.textContent = data;
        })
        .catch(error => {
            console.error("Error:", error);
        });
    });
});
