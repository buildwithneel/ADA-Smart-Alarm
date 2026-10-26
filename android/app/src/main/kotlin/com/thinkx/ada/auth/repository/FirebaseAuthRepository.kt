package com.thinkx.ada.auth.repository

import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseAuthException
import com.google.firebase.auth.FirebaseAuthInvalidCredentialsException
import com.google.firebase.auth.FirebaseAuthInvalidUserException
import com.google.firebase.auth.FirebaseAuthUserCollisionException
import com.google.firebase.auth.FirebaseAuthWeakPasswordException
import com.google.firebase.auth.FirebaseUser
import com.google.firebase.auth.GoogleAuthProvider
import com.google.firebase.auth.UserProfileChangeRequest
import com.thinkx.ada.auth.model.AuthState
import com.thinkx.ada.auth.model.AuthUser
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withContext

/**
 * Production implementation of [AuthRepository] backed by the official Firebase Android SDK.
 */
class FirebaseAuthRepository(
    private val firebaseAuth: FirebaseAuth? = null,
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.IO)
) : AuthRepository {

    private val auth: FirebaseAuth? by lazy {
        firebaseAuth ?: try {
            FirebaseAuth.getInstance()
        } catch (_: Exception) {
            null
        }
    }

    private val _authStateFlow = MutableStateFlow<AuthState>(AuthState.Loading)
    override val authStateFlow: StateFlow<AuthState> = _authStateFlow.asStateFlow()

    override val currentUser: AuthUser?
        get() = auth?.currentUser?.toDomain()

    init {
        val currentAuth = auth
        if (currentAuth != null) {
            currentAuth.addAuthStateListener { fbAuth ->
                val fbUser = fbAuth.currentUser
                if (fbUser != null) {
                    _authStateFlow.value = AuthState.Authenticated(fbUser.toDomain())
                } else {
                    _authStateFlow.value = AuthState.Unauthenticated()
                }
            }
        } else {
            _authStateFlow.value = AuthState.Unauthenticated("Firebase Authentication is not initialized.")
        }
    }

    override suspend fun getIdToken(forceRefresh: Boolean): Result<String> = withContext(Dispatchers.IO) {
        val user = auth?.currentUser
            ?: return@withContext Result.failure(IllegalStateException("No authenticated user session found."))
        try {
            val tokenResult = user.getIdToken(forceRefresh).await()
            val token = tokenResult.token
            if (!token.isNullOrBlank()) {
                Result.success(token)
            } else {
                Result.failure(IllegalStateException("Received empty ID token from Firebase."))
            }
        } catch (e: Exception) {
            Result.failure(mapFirebaseError(e))
        }
    }

    override suspend fun signInWithEmail(email: String, pass: String): Result<AuthUser> = withContext(Dispatchers.IO) {
        val safeAuth = auth ?: return@withContext Result.failure(IllegalStateException("Firebase is not initialized."))
        try {
            val authResult = safeAuth.signInWithEmailAndPassword(email.trim(), pass).await()
            val user = authResult.user?.toDomain()
                ?: return@withContext Result.failure(IllegalStateException("Sign in succeeded but user is null."))
            Result.success(user)
        } catch (e: Exception) {
            Result.failure(mapFirebaseError(e))
        }
    }

    override suspend fun registerWithEmail(
        email: String,
        pass: String,
        displayName: String?
    ): Result<AuthUser> = withContext(Dispatchers.IO) {
        val safeAuth = auth ?: return@withContext Result.failure(IllegalStateException("Firebase is not initialized."))
        try {
            val authResult = safeAuth.createUserWithEmailAndPassword(email.trim(), pass).await()
            val fbUser = authResult.user
                ?: return@withContext Result.failure(IllegalStateException("Registration succeeded but user is null."))

            if (!displayName.isNullOrBlank()) {
                try {
                    val updateProfile = UserProfileChangeRequest.Builder()
                        .setDisplayName(displayName.trim())
                        .build()
                    fbUser.updateProfile(updateProfile).await()
                } catch (_: Exception) {
                    // Profile display name update is non-fatal for account registration
                }
            }

            Result.success(fbUser.toDomain())
        } catch (e: Exception) {
            Result.failure(mapFirebaseError(e))
        }
    }

    override suspend fun signInWithGoogleCredential(idToken: String): Result<AuthUser> = withContext(Dispatchers.IO) {
        val safeAuth = auth ?: return@withContext Result.failure(IllegalStateException("Firebase is not initialized."))
        try {
            val credential = GoogleAuthProvider.getCredential(idToken, null)
            val authResult = safeAuth.signInWithCredential(credential).await()
            val user = authResult.user?.toDomain()
                ?: return@withContext Result.failure(IllegalStateException("Google sign in succeeded but user is null."))
            Result.success(user)
        } catch (e: Exception) {
            Result.failure(mapFirebaseError(e))
        }
    }

    override suspend fun sendPasswordReset(email: String): Result<Unit> = withContext(Dispatchers.IO) {
        val safeAuth = auth ?: return@withContext Result.failure(IllegalStateException("Firebase is not initialized."))
        try {
            safeAuth.sendPasswordResetEmail(email.trim()).await()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(mapFirebaseError(e))
        }
    }

    override suspend fun signOut(): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            auth?.signOut()
            _authStateFlow.value = AuthState.Unauthenticated()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private fun FirebaseUser.toDomain(): AuthUser {
        return AuthUser(
            uid = uid,
            email = email,
            displayName = displayName,
            photoUrl = photoUrl?.toString(),
            isEmailVerified = isEmailVerified
        )
    }

    private fun mapFirebaseError(e: Exception): Exception {
        val message = when (e) {
            is FirebaseAuthInvalidUserException -> "No account found matching these credentials."
            is FirebaseAuthInvalidCredentialsException -> "Invalid email address or password."
            is FirebaseAuthUserCollisionException -> "An account with this email address already exists."
            is FirebaseAuthWeakPasswordException -> "Password is too weak. Please use at least 6 characters."
            is FirebaseAuthException -> e.message ?: "Authentication failed."
            else -> e.localizedMessage ?: "Network or server connection failed."
        }
        return Exception(message, e)
    }
}
