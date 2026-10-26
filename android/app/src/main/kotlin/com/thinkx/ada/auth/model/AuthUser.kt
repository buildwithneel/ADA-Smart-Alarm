package com.thinkx.ada.auth.model

/**
 * Domain representation of an authenticated user identity.
 * Maps from FirebaseUser while avoiding tight framework coupling in domain and UI layers.
 */
data class AuthUser(
    val uid: String,
    val email: String?,
    val displayName: String?,
    val photoUrl: String? = null,
    val isEmailVerified: Boolean = false
)
