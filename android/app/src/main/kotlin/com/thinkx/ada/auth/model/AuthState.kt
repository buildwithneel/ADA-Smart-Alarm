package com.thinkx.ada.auth.model

/**
 * State of user authentication in the ADA Smart Alarm app.
 */
sealed interface AuthState {
    data object Loading : AuthState
    data class Authenticated(val user: AuthUser) : AuthState
    data class Unauthenticated(val message: String? = null) : AuthState
}
