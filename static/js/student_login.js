document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('student-login-form');
    const loginError = document.getElementById('login-error');

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const rollNumber = document.getElementById('roll-number').value.trim();
            const day = document.getElementById('dob-day').value.padStart(2, '0');
            const month = document.getElementById('dob-month').value.padStart(2, '0');
            const year = document.getElementById('dob-year').value;
            const dob = `${year}-${month}-${day}`;
            
            try {
                const res = await fetch('/api/student/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ rollnumber: rollNumber, dob: dob })
                });
                
                const data = await res.json();
                
                if (data.success) {
                    // Redirect to the student map dashboard upon successful login
                    window.location.href = "/";
                } else {
                    loginError.textContent = data.message || "Invalid Student Details";
                    loginError.style.display = 'block';
                }
            } catch (err) {
                console.error("Login Error:", err);
                loginError.textContent = 'Network error. Please try again.';
                loginError.style.display = 'block';
            }
        });
    }
});
