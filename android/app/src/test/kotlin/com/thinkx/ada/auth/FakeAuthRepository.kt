package com.thinkx.ada.auth

import com.thinkx.ada.auth.model.AuthState
import com.thinkx.ada.auth.model.AuthUser
import com.thinkx.ada.auth.repository.AuthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class FakeAuthRepository(
    initialUser: AuthUser? = null,
    var mockToken: String? = "mock-firebase-id-token-12345",
    var shouldFail: Boolean = false,
    var failureMessage: String = "Simulated authentication failure"
) : AuthRepository {

    private val _authStateFlow = MutableStateFlow<AuthState>(
        if (initialUser != null) AuthState.Authenticated(initialUser) else AuthState.Unauthenticated()
    )
    override val authStateFlow: StateFlow<AuthState> = _authStateFlow.asStateFlow()

    override var currentUser: AuthUser? = initialUser

    var idTokenCallCount = 0
    var lastForceRefresh: Boolean? = null
    var signOutCallCount = 0
    var passwordResetEmails = mutableListOf<String>()

    fun setAuthenticated(user: AuthUser) {
        currentUser = user
        _authStateFlow.value = AuthState.Authenticated(user)
    }

    fun setUnauthenticated(message: String? = null) {
        currentUser = null
        _authStateFlow.value = AuthState.Unauthenticated(message)
    }

    override suspend fun getIdToken(forceRefresh: Boolean): Result<String> {
        idTokenCallCount++
        lastForceRefresh = forceRefresh
        if (shouldFail) return Result.failure(Exception(failureMessage))
        return if (mockToken != null) Result.success(mockToken!!) else Result.failure(IllegalStateException("No token"))
    }

    override suspend fun signInWithEmail(email: String, pass: String): Result<AuthUser> {
        if (shouldFail) return Result.failure(Exception(failureMessage))
        val user = AuthUser(uid = "uid-${email.hashCode()}", email = email, displayName = "Test User")
        setAuthenticated(user)
        return Result.success(user)
    }

    override suspend fun registerWithEmail(
        email: String,
        pass: String,
        displayName: String?
    ): Result<AuthUser> {
        if (shouldFail) return Result.failure(Exception(failureMessage))
        val user = AuthUser(uid = "uid-${email.hashCode()}", email = email, displayName = displayName ?: "User")
        setAuthenticated(user)
        return Result.success(user)
    }

    override suspend fun signInWithGoogleCredential(idToken: String): Result<AuthUser> {
        if (shouldFail) return Result.failure(Exception(failureMessage))
        val user = AuthUser(uid = "google-uid-001", email = "google@ada.com", displayName = "Google User")
        setAuthenticated(user)
        return Result.success(user)
    }

    override suspend fun sendPasswordReset(email: String): Result<Unit> {
        if (shouldFail) return Result.failure(Exception(failureMessage))
        passwordResetEmails.add(email)
        return Result.success(Unit)
    }

    override suspend fun signOut(): Result<Unit> {
        signOutCallCount++
        setUnauthenticated()
        return Result.success(Unit)
    }
}
