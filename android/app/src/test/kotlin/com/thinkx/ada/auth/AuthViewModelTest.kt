package com.thinkx.ada.auth

import com.thinkx.ada.auth.model.AuthState
import com.thinkx.ada.auth.model.AuthUser
import com.thinkx.ada.auth.ui.AuthMode
import com.thinkx.ada.auth.ui.AuthViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class AuthViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var authRepository: FakeAuthRepository
    private lateinit var viewModel: AuthViewModel

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        authRepository = FakeAuthRepository()
        viewModel = AuthViewModel(authRepository)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun initialState_isLoginModeWithEmptyFields() {
        val state = viewModel.uiState.value
        assertEquals(AuthMode.LOGIN, state.mode)
        assertEquals("", state.email)
        assertEquals("", state.password)
        assertFalse(state.isLoading)
        assertNull(state.errorMessage)
        assertNull(state.successMessage)
    }

    @Test
    fun setMode_switchesModeAndClearsMessages() {
        viewModel.setMode(AuthMode.REGISTER)
        assertEquals(AuthMode.REGISTER, viewModel.uiState.value.mode)

        viewModel.setMode(AuthMode.FORGOT_PASSWORD)
        assertEquals(AuthMode.FORGOT_PASSWORD, viewModel.uiState.value.mode)
    }

    @Test
    fun submit_invalidEmail_setsValidationError() = runTest {
        viewModel.onEmailChange("not-an-email")
        viewModel.onPasswordChange("validpass123")
        viewModel.submit()

        val state = viewModel.uiState.value
        assertNotNull(state.errorMessage)
        assertTrue(state.errorMessage!!.contains("valid email", ignoreCase = true))
    }

    @Test
    fun submit_emptyPasswordInLogin_setsValidationError() = runTest {
        viewModel.onEmailChange("user@ada.com")
        viewModel.onPasswordChange("")
        viewModel.submit()

        val state = viewModel.uiState.value
        assertNotNull(state.errorMessage)
        assertTrue(state.errorMessage!!.contains("password", ignoreCase = true))
    }

    @Test
    fun submit_shortPasswordInRegister_setsValidationError() = runTest {
        viewModel.setMode(AuthMode.REGISTER)
        viewModel.onEmailChange("user@ada.com")
        viewModel.onPasswordChange("123")
        viewModel.onConfirmPasswordChange("123")
        viewModel.submit()

        val state = viewModel.uiState.value
        assertNotNull(state.errorMessage)
        assertTrue(state.errorMessage!!.contains("at least 6", ignoreCase = true))
    }

    @Test
    fun submit_passwordMismatchInRegister_setsValidationError() = runTest {
        viewModel.setMode(AuthMode.REGISTER)
        viewModel.onEmailChange("user@ada.com")
        viewModel.onPasswordChange("password123")
        viewModel.onConfirmPasswordChange("mismatched123")
        viewModel.submit()

        val state = viewModel.uiState.value
        assertNotNull(state.errorMessage)
        assertTrue(state.errorMessage!!.contains("do not match", ignoreCase = true))
    }

    @Test
    fun executeSignIn_success_setsSuccessStateAndMessage() = runTest {
        viewModel.onEmailChange("user@ada.com")
        viewModel.onPasswordChange("securepassword")
        viewModel.submit()

        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertFalse(state.isLoading)
        assertTrue(state.isSuccess)
        assertNotNull(state.successMessage)
        assertNull(state.errorMessage)
    }

    @Test
    fun executeSignIn_failure_setsErrorMessage() = runTest {
        authRepository.shouldFail = true
        authRepository.failureMessage = "Invalid credentials."

        viewModel.onEmailChange("wrong@ada.com")
        viewModel.onPasswordChange("wrongpassword")
        viewModel.submit()

        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertFalse(state.isLoading)
        assertFalse(state.isSuccess)
        assertEquals("Invalid credentials.", state.errorMessage)
    }

    @Test
    fun executeRegister_success_authenticatesAndSetsSuccessMessage() = runTest {
        viewModel.setMode(AuthMode.REGISTER)
        viewModel.onDisplayNameChange("Ada Pioneer")
        viewModel.onEmailChange("pioneer@ada.com")
        viewModel.onPasswordChange("longsecurepass")
        viewModel.onConfirmPasswordChange("longsecurepass")
        viewModel.submit()

        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertTrue(state.isSuccess)
        assertNull(state.errorMessage)
        assertEquals("Account created successfully.", state.successMessage)
    }

    @Test
    fun executePasswordReset_recordsEmailAndSetsSuccess() = runTest {
        viewModel.setMode(AuthMode.FORGOT_PASSWORD)
        viewModel.onEmailChange("forgot@ada.com")
        viewModel.submit()

        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertTrue(authRepository.passwordResetEmails.contains("forgot@ada.com"))
        assertNotNull(state.successMessage)
        assertTrue(state.successMessage!!.contains("forgot@ada.com"))
    }

    @Test
    fun signInWithGoogleIdToken_success_authenticatesUser() = runTest {
        viewModel.signInWithGoogleIdToken("google-test-id-token")

        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertTrue(state.isSuccess)
        assertNotNull(state.successMessage)
        assertTrue(state.successMessage!!.contains("Google User"))
    }

    @Test
    fun signOut_invokesRepositoryAndResetsState() = runTest {
        authRepository.setAuthenticated(AuthUser("uid-1", "user@ada.com", "User"))
        viewModel.signOut()

        advanceUntilIdle()

        assertEquals(1, authRepository.signOutCallCount)
        assertTrue(authRepository.authStateFlow.value is AuthState.Unauthenticated)
    }
}
