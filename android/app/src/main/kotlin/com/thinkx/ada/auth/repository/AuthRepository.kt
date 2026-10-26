package com.thinkx.ada.auth.repository

import com.thinkx.ada.auth.model.AuthState
import com.thinkx.ada.auth.model.AuthUser
import kotlinx.coroutines.flow.StateFlow

/**
 * Contract for authentication operations and state observation.
 */
interface AuthRepository {
    val authStateFlow: StateFlow<AuthState>
    val currentUser: AuthUser?

    suspend fun getIdToken(forceRefresh: Boolean = false): Result<String>
    suspend fun signInWithEmail(email: String, pass: String): Result<AuthUser>
    suspend fun registerWithEmail(email: String, pass: String, displayName: String? = null): Result<AuthUser>
    suspend fun signInWithGoogleCredential(idToken: String): Result<AuthUser>
    suspend fun sendPasswordReset(email: String): Result<Unit>
    suspend fun signOut(): Result<Unit>
}
