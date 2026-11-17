# QIS Authentication System — Comprehensive Initial Audit Report

**Date:** November 16, 2026  
**Auditor:** Senior Full-Stack & Application Security Engineer  
**System Under Audit:** QIS (AI-Assisted Assessment Intelligence Platform)  
**Scope:** Authentication Architecture, Security Controls, API Routes, Database Models, Frontend Pages & UI/UX  

---

## 1. Existing System Architecture Overview

| Layer | Technology | Current Implementation |
|---|---|---|
| **Frontend Framework** | React 19.2.0, Vite 7.2.4 | Single Page Application (SPA) using `react-router-dom` v7.10.1, Bootstrap 5.3.8, Lucide React |
| **Backend Framework** | FastAPI 0.104.1 (ASGI), Uvicorn 0.24.0 | RESTful API with route modules mounted under `/api/*` |
| **Database & ORM** | SQLite / SQLAlchemy 2.0.23 | Instance SQLite database located at `backend/instance/intranet_exam_db.db` |
| **Auth Mechanism** | PyJWT 2.8.0 | Bare JWT with HS256 algorithm; stored in browser `localStorage` |
| **Password Hashing** | Werkzeug 3.0.1 (`generate_password_hash`) | PBKDF2/SHA256 and Scrypt hashes; `bcrypt` (4.1.1) and `passlib` (1.7.4) are installed in `.venv` but unutilized |
| **Authorization** | Role-Based Access Control (RBAC) | Fast-path roles (`student`, `teacher`, `admin`) enforced via dependency injection in `auth_middleware.py` |

---

## 2. Inventory of Existing Auth Components & Endpoints

### 2.1 Backend Endpoints
- **`POST /api/auth/login`** (`backend/routes/main_routes.py` line 99):
  - Accepts `{ "username": "...", "password": "..." }`.
  - Searches database strictly by `username` (ignoring email lookup).
  - Issues token: `jwt.encode({'user_id': user.id, 'role': user.role}, SECRET_KEY, algorithm="HS256")`.
  - Returns `{"token": token, "user": {"id": user.id, "username": user.username, "role": user.role}}`.
- **`GET /api/admin/users`** & **`POST /api/admin/users`** (`backend/routes/admin_routes.py`):
  - Admin-only endpoint to list and provision users.
- **`POST /api/students/bulk_add`** (`backend/routes/students_routes.py`):
  - Teacher-only bulk student creation with auto-generated placeholder emails.
- **Missing Endpoints:**
  - ❌ User registration (`POST /api/auth/register`)
  - ❌ Email verification (`POST /api/auth/verify-email`, `POST /api/auth/resend-verification`)
  - ❌ Password recovery (`POST /api/auth/forgot-password`, `POST /api/auth/verify-reset-token`, `POST /api/auth/reset-password`)
  - ❌ Token refresh and session management (`POST /api/auth/refresh`, `POST /api/auth/logout`)
  - ❌ User profile and credentials management (`GET /api/auth/me`, `PUT /api/auth/profile`, `POST /api/auth/change-password`)
  - ❌ OAuth 2.0 / OIDC social login (`/api/auth/oauth/*`)

### 2.2 Database Models (`backend/models.py`)
- **`User` table:**
  - Columns: `id`, `enrollment_id`, `username`, `email`, `password_hash`, `role`, `is_active`.
  - ❌ Missing: `full_name` / `name` column.
  - ❌ Missing: `is_verified` / `email_verified_at` column.
  - ❌ Missing: timestamps (`created_at`, `updated_at`).
  - ❌ Missing: `email_verification_token` table.
  - ❌ Missing: `password_reset_token` table.
  - ❌ Missing: `refresh_token` table.
  - ❌ Missing: `oauth_account` table.
  - ❌ Missing: `security_log` table.

### 2.3 Frontend Pages & UI/UX (`frontend/src/`)
- **`LoginPage.jsx`:**
  - Minimal form with two inputs (username, password) and submit button.
  - Hardcoded test account credentials displayed on screen.
  - ❌ No registration navigation link.
  - ❌ No "Forgot Password?" link.
  - ❌ No password visibility toggle.
  - ❌ No "Remember Me" checkbox.
  - ❌ No OAuth (Google / GitHub) sign-in buttons.
  - ❌ No email format validation or input sanitization.
- **Missing Pages:**
  - ❌ Registration Page (`RegisterPage.jsx`)
  - ❌ Email Verification Page (`VerifyEmailPage.jsx`)
  - ❌ Forgot Password Page (`ForgotPasswordPage.jsx`)
  - ❌ Reset Password Page (`ResetPasswordPage.jsx`)
  - ❌ User Profile & Account Settings (`ProfilePage.jsx`)
  - ❌ OAuth Callback Handler (`OAuthCallbackPage.jsx`)
- **`AuthContext.jsx`:**
  - Stores credentials in browser `localStorage`.
  - ❌ No token expiration checking.
  - ❌ No refresh token rotation or automatic token renewal.
  - ❌ No registration or password recovery API wrappers.

---

## 3. Critical Security Vulnerabilities Identified

### 🚨 VULN-01: Non-Expiring JWT Tokens (High Severity)
- **Finding:** In `main_routes.py` line 107:
  ```python
  token = jwt.encode(
      {'user_id': user.id, 'role': user.role},
      getattr(Config, 'SECRET_KEY', 'my_precious_secret'),
      algorithm="HS256"
  )
  ```
- **Risk:** The JWT payload contains **no `exp` claim** (expiration time) and no `iat` (issued at). Once generated, a token remains valid indefinitely. Any intercepted or leaked token permits permanent unauthorized account access.

### 🚨 VULN-02: Missing Account Invalidation / Inactive User Bypass (High Severity)
- **Finding:** In `auth_middleware.py`:
  ```python
  payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
  user_id: int = payload.get("user_id")
  user = db.get(User, user_id)
  if user is None:
      raise credentials_exception
  return user
  ```
- **Risk:** `user.is_active` is completely uninspected. Even if an administrator deactivates a compromised or expelled user (`is_active = False`), existing tokens remain 100% functional.

### 🚨 VULN-03: No Brute-Force Protection & Rate Limiting (High Severity)
- **Finding:** `/api/auth/login` possesses no throttling, IP rate limiting, or account lockout mechanism.
- **Risk:** Automated credential stuffing, password guessing, and denial-of-service against the database authentication pathway are unmitigated.

### 🚨 VULN-04: Storage of Authentication Tokens in `localStorage` (Medium Severity)
- **Finding:** Both access tokens and user profile objects are persisted in `window.localStorage`.
- **Risk:** Vulnerable to Cross-Site Scripting (XSS). If any third-party script or unescaped user-generated content executes JavaScript in the origin, tokens can be extracted.

### 🚨 VULN-05: Missing User Registration & Email Verification (High Severity)
- **Finding:** Prospective students and users cannot register themselves. Only administrators and teachers can manually seed accounts. There is zero email verification flow.
- **Risk:** Unverified email addresses and lack of standard identity onboarding.

### 🚨 VULN-06: Missing Password Recovery Mechanism (High Severity)
- **Finding:** No forgot password or reset password capability exists anywhere in the codebase.
- **Risk:** Account lockout requires manual database inspection or administrator intervention.

### 🚨 VULN-07: Inconsistent Password Hashing Algorithms (Medium Severity)
- **Finding:** User passwords use Werkzeug default hashes without modern salt configuration or migration path to Bcrypt/Argon2.
- **Risk:** Sub-optimal cryptographic cost parameters for newly created accounts.

---

## 4. Implementation & Remediation Plan

1. **Database Schema Enhancements:**
   - Update `models.py` with `full_name`, `is_verified`, `created_at`, `updated_at` on `User`.
   - Add `EmailVerificationToken`, `PasswordResetToken`, `RefreshToken`, `OAuthAccount`, and `SecurityLog` models.
   - Execute safe, non-destructive migration script backing up `intranet_exam_db.db` and applying alterations without data loss.

2. **Security & Cryptography Engine (`security_service.py`):**
   - Implement bcrypt hashing with automatic legacy hash verification & upgrade.
   - Implement cryptographically secure token generation (single-use, hashed via SHA-256 before database storage).
   - Implement token expiration policies (Access Token: 30 minutes; Refresh Token: 7-30 days; Verification: 24h; Reset: 1h).
   - Implement in-memory sliding-window rate limiting & brute-force account lockout.

3. **Email Notification Engine (`email_service.py`):**
   - Provide SMTP client supporting TLS/SSL.
   - Implement local development logger/file outbox for headless testing environments.
   - Professional HTML & text email templates for verification and password reset.

4. **OAuth 2.0 / Social Authentication (`oauth_service.py`):**
   - Google & GitHub OAuth 2.0 flows with state, nonce, and PKCE verification.
   - Secure account linking: match only verified emails to prevent account takeover.
   - Automatic student role assignment (zero privilege escalation).
   - Safe unconfigured state detection when credentials are missing.

5. **Clean Modular API Endpoints (`backend/routes/auth_routes.py`):**
   - Complete implementation of all 12 auth endpoints.
   - Generic, enumeration-resistant error responses.
   - HttpOnly + SameSite cookies paired with Bearer token header support.

6. **Frontend UI/UX Overhaul (`frontend/src/`):**
   - Redesign `LoginPage.jsx` to match QIS visual design language.
   - Create `RegisterPage.jsx` with real-time password strength meter and validation.
   - Create `VerifyEmailPage.jsx`, `ForgotPasswordPage.jsx`, `ResetPasswordPage.jsx`, `ProfilePage.jsx`, and `OAuthCallbackPage.jsx`.
   - Update `app.jsx` routing and `Navbar.jsx` user status badge.

7. **Verification & Automated Testing:**
   - Develop comprehensive end-to-end unit and integration test suite covering all 12 requirement areas.
   - Verify frontend builds and runs cleanly.

