package com.thinkx.ada

import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation3.runtime.entryProvider
import androidx.navigation3.runtime.rememberNavBackStack
import androidx.navigation3.ui.NavDisplay
import com.thinkx.ada.auth.ui.AuthScreen
import com.thinkx.ada.auth.ui.AuthViewModel
import com.thinkx.ada.ui.alarm.CreateEditAlarmScreen
import com.thinkx.ada.ui.alarm.CreateEditAlarmViewModel
import com.thinkx.ada.ui.destinations.DestinationsScreen
import com.thinkx.ada.ui.destinations.DestinationsViewModel
import com.thinkx.ada.ui.home.HomeScreen
import com.thinkx.ada.ui.home.HomeViewModel
import com.thinkx.ada.ui.settings.SettingsScreen
import com.thinkx.ada.ui.settings.SettingsViewModel

@Composable
fun MainNavigation() {
    val context = LocalContext.current
    val app = context.applicationContext as AdaApplication
    val backStack = rememberNavBackStack(Main)

    NavDisplay(
        backStack = backStack,
        onBack = { backStack.removeLastOrNull() },
        entryProvider = entryProvider {
            entry<Main> {
                HomeScreen(
                    viewModel = viewModel(
                        factory = HomeViewModel.Factory(
                            alarmRepository = app.alarmRepository,
                            alarmScheduler = app.alarmScheduler,
                            syncRepository = app.syncRepository,
                            journeyScheduler = app.journeyScheduler
                        )
                    ),
                    onCreateAlarmClick = { backStack.add(CreateEditAlarm()) },
                    onEditAlarmClick = { alarmId -> backStack.add(CreateEditAlarm(alarmId)) },
                    onDestinationsClick = { backStack.add(Destinations) },
                    onSettingsClick = { backStack.add(Settings) },
                    onAccountClick = { backStack.add(Auth) }
                )
            }

            entry<CreateEditAlarm> { key ->
                CreateEditAlarmScreen(
                    viewModel = viewModel(
                        key = key.alarmId ?: "new_alarm",
                        factory = CreateEditAlarmViewModel.Factory(
                            alarmId = key.alarmId,
                            alarmRepository = app.alarmRepository,
                            destinationRepository = app.destinationRepository,
                            userPreferencesRepository = app.userPreferencesRepository,
                            alarmScheduler = app.alarmScheduler,
                            syncRepository = app.syncRepository,
                            journeyScheduler = app.journeyScheduler
                        )
                    ),
                    onNavigateBack = { backStack.removeLastOrNull() }
                )
            }

            entry<Destinations> {
                DestinationsScreen(
                    viewModel = viewModel(
                        factory = DestinationsViewModel.Factory(
                            destinationRepository = app.destinationRepository
                        )
                    ),
                    onNavigateBack = { backStack.removeLastOrNull() }
                )
            }

            entry<Settings> {
                SettingsScreen(
                    viewModel = viewModel(
                        factory = SettingsViewModel.Factory(
                            userPreferencesRepository = app.userPreferencesRepository,
                            alarmScheduler = app.alarmScheduler
                        )
                    ),
                    onNavigateBack = { backStack.removeLastOrNull() },
                    onAccountClick = { backStack.add(Auth) }
                )
            }

            entry<Auth> {
                AuthScreen(
                    viewModel = viewModel(
                        factory = AuthViewModel.Factory(
                            authRepository = app.authRepository
                        )
                    ),
                    onAuthSuccess = { backStack.removeLastOrNull() },
                    onNavigateBack = { backStack.removeLastOrNull() }
                )
            }
        }
    )
}
