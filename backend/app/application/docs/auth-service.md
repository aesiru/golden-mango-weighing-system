<!-- SCOPE: Application service documentation for authentication orchestration -->
<!-- DOC_KIND: reference -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Understanding authentication architecture, implementing auth flows, troubleshooting authentication issues -->
<!-- SKIP_WHEN: Quick API reference - use the Quick Navigation section -->
<!-- PRIMARY_SOURCES: backend/app/application/services/auth_service.py, backend/app/api/routes/auth.py, backend/app/infrastructure/auth/ -->

# Auth Service

## Quick Navigation

- [Architecture](#architecture) - Service design and dependencies
- [API Endpoints](#api-endpoints) - Authentication REST API specifications
- [Core Operations](#core-operations) - Login, refresh, and validation flows
- [Frontend Integration](#frontend-integration) - Auth store and route protection
- [JWT Configuration](#jwt-configuration) - Token settings and security
- [Security Considerations](#security-considerations) - Password and token security
- [Testing](#testing) - Test strategies and coverage
- [Error Handling](#error-handling) - Common error scenarios and resolutions

## Agent Entry

**Purpose**: The Auth Service orchestrates authentication logic including user login, JWT token generation, token refresh, and token validation. It bridges the domain authentication logic with infrastructure JWT and password services.

**When to Read**:

- Implementing authentication flows in frontend components
- Troubleshooting login or token refresh issues
- Understanding JWT token structure and validation
- Setting up authentication middleware

**When to Skip**: Quick API endpoint lookup - use the Quick Navigation section above

**Canonical**: This is the primary reference for authentication service architecture and integration patterns

**Next**: Read Architecture section to understand dependencies, then API Endpoints for integration details

**Primary Sources**:

- `backend/app/application/services/auth_service.py` - Core service implementation
- `backend/app/api/routes/auth.py` - REST API endpoints
- `backend/app/infrastructure/auth/` - JWT and password services

## Overview

The Auth Service orchestrates authentication logic including user login, JWT token generation, token refresh, and token validation. It bridges the domain authentication logic with infrastructure JWT and password services.

## Architecture

### Domain Model

```
┌─────────────────────────────────────┐
│   AuthService                       │
├─────────────────────────────────────┤
│   auth_repo: AuthRepository         │
│   jwt_service: JWTService           │
│   password_service: PasswordService │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│   AuthenticatedUser                 │
├─────────────────────────────────────┤
│   id: str                           │
│   username: str                     │
│   roles: list[str]                  │
│   role_ids: list[str]               │
│   is_superuser: bool                │
└─────────────────────────────────────┘
```

**Dependencies:**

- `auth_repo`: User data access and role resolution
- `jwt_service`: JWT token creation and validation
- `password_service`: Password hashing and verification

## API Endpoints

**Base:** `/api/v1/auth`

| Endpoint   | Method | Description                              |
| ---------- | ------ | ---------------------------------------- |
| `/login`   | POST   | Authenticate user, return tokens         |
| `/refresh` | POST   | Refresh access token using refresh token |
| `/me`      | GET    | Get current authenticated user info      |

### Request/Response Patterns

**Login Request:**

```json
{
  "username": "admin",
  "password": "secret"
}
```

**Login Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "USR-001",
    "username": "admin",
    "roles": ["Administrator", "Manager"],
    "role_ids": ["role_1", "role_2"],
    "is_superuser": true
  }
}
```

**Refresh Request:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Refresh Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

## Core Operations

### Login Flow

1. **Fetch User:** Retrieve user by username from repository
2. **Verify Password:** Check password against bcrypt hash
3. **Check Active Status:** Ensure user account is enabled
4. **Generate Tokens:** Create access and refresh JWT tokens
5. **Return User:** Include roles and permissions in response

**Error Scenarios:**

- User not found → `EntityNotFoundError`
- Invalid password → `PermissionDeniedError`
- Account disabled → `PermissionDeniedError`

### Token Refresh Flow

1. **Decode Token:** Validate refresh token signature and expiry
2. **Check Type:** Ensure token type is "refresh"
3. **Fetch User:** Verify user still exists and is active
4. **Generate New Token:** Issue new access token

**Error Scenarios:**

- Invalid signature → `PermissionDeniedError`
- Wrong token type → `PermissionDeniedError`
- User disabled → `PermissionDeniedError`

### Token Validation

Used by middleware to protect routes:

1. **Decode Token:** Extract payload without validation
2. **Fetch User:** Load user from database
3. **Return User:** Provide `AuthenticatedUser` for route handlers

Returns `None` for invalid/expired tokens.

## Frontend Integration

### Authentication Flow

**Login Page:** `frontend/app/pages/login.vue`

```typescript
const authStore = useAuthStore();

// Login
await authStore.login({ username, password });

// Token storage handled automatically via HTTP-only cookies
// OR localStorage for SPA mode
```

**Token Refresh:**

```typescript
// Automatic on 401 responses via Axios interceptor
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      await authStore.refreshToken();
      return api.request(error.config);
    }
    return Promise.reject(error);
  },
);
```

### Auth Store

**Pinia Store:** `useAuthStore()`

```typescript
const authStore = useAuthStore();

// State
authStore.user; // AuthenticatedUser | null
authStore.isAuthenticated; // boolean
authStore.roles; // string[]

// Actions
authStore.login(credentials);
authStore.logout();
authStore.refreshToken();
authStore.fetchUser();
```

### Route Protection

**Middleware:** `frontend/app/middleware/auth.ts`

```typescript
export default defineNuxtRouteMiddleware((to, from) => {
  const authStore = useAuthStore();

  if (!authStore.isAuthenticated) {
    return navigateTo("/login");
  }

  // Check required roles
  if (to.meta.requiredRole && !authStore.hasRole(to.meta.requiredRole)) {
    return navigateTo("/403");
  }
});
```

## JWT Configuration

**Token Lifetimes:**

- Access Token: 15 minutes
- Refresh Token: 7 days

**Algorithm:** HS256

**Claims:**

- `sub`: Username
- `user_id`: User ID
- `type`: "access" | "refresh"
- `exp`: Expiration timestamp
- `iat`: Issued at timestamp

**Configuration Location:**

- `backend/app/core/config.py`
- `SECRET_KEY`: Environment variable for signing

## Security Considerations

### Password Handling

- **Hashing:** bcrypt with salt rounds = 12
- **Storage:** Never store plain text passwords
- **Validation:** Constant-time comparison to prevent timing attacks

### Token Security

- **HTTP-only Cookies:** Preferred for web clients
- **Secure Flag:** Required for HTTPS deployments
- **SameSite:** Strict or Lax depending on use case
- **Storage:** LocalStorage fallback for SPA mode

### Rate Limiting

- Login attempts: 5 per minute per IP
- Token refresh: 10 per minute per user
- Brute force protection via progressive delays

## Testing

**Unit Tests:** `backend/tests/test_auth_service.py`

Test scenarios:

- Successful login with valid credentials
- Failed login with wrong password
- Failed login for disabled user
- Token refresh with valid refresh token
- Token refresh with expired token
- Token validation with valid/invalid tokens
- Superuser flag propagation

**Integration Tests:**

- Full login → protected route → logout flow
- Token expiration and automatic refresh
- Concurrent session handling

## Error Handling

| Error                 | HTTP Status | Frontend Action                                |
| --------------------- | ----------- | ---------------------------------------------- |
| Invalid credentials   | 401         | Show error message, clear password field       |
| Account disabled      | 403         | Show account locked message                    |
| Token expired         | 401         | Attempt silent refresh, else redirect to login |
| Invalid refresh token | 401         | Redirect to login page                         |

## Future Enhancements

- Multi-factor authentication (MFA)
- OAuth2 / OpenID Connect integration
- Session management (view active sessions, revoke)
- Password policy enforcement
- Account lockout after failed attempts
- Email verification for new accounts
- Password reset flow

## Maintenance

**Update Triggers**:

- Authentication flow changes
- New JWT token claims or validation rules
- Password policy updates
- Security requirement changes
- New authentication methods added

**Verification**:

- Run `pytest tests/test_auth_service.py` - all tests must pass
- Verify login flow works with test credentials
- Test token refresh mechanism
- Validate rate limiting functionality
- Check JWT configuration matches security requirements
- Confirm frontend auth store integration

**Last Updated**: 2026-04-05
