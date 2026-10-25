package com.thinkx.ada.ui.main

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation3.runtime.NavKey
import com.thinkx.ada.R
import com.thinkx.ada.data.DefaultDataRepository
import com.thinkx.ada.ui.theme.ADASmartAlarmTheme

@Composable
fun MainScreen(
  onItemClick: (NavKey) -> Unit,
  modifier: Modifier = Modifier,
  viewModel: MainScreenViewModel = viewModel { MainScreenViewModel(DefaultDataRepository()) },
) {
  val uiState by viewModel.uiState.collectAsStateWithLifecycle()
  when (val state = uiState) {
    MainScreenUiState.Loading -> {
      Box(
        modifier = modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
      ) {
        CircularProgressIndicator()
      }
    }
    is MainScreenUiState.Success -> {
      MainScreen(data = state.data, modifier = modifier)
    }
    is MainScreenUiState.Error -> {
      Text("Error loading data: ${state.throwable.message}")
    }
  }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun MainScreen(data: List<String>, modifier: Modifier = Modifier) {
  Scaffold(
    modifier = modifier,
    topBar = {
      CenterAlignedTopAppBar(
        title = { Text(stringResource(R.string.app_name)) },
        colors = TopAppBarDefaults.topAppBarColors(
          containerColor = MaterialTheme.colorScheme.primaryContainer,
          titleContentColor = MaterialTheme.colorScheme.primary
        )
      )
    }
  ) { innerPadding ->

    // App Content

    Column(
      modifier = Modifier.padding(innerPadding),
      verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
      data.forEach { Greeting(it) }
      Button(
        modifier = Modifier.padding(24.dp, 24.dp),
        onClick = { /* Button clicked */ }
      ) {
        Text("OK")
      }

      // TODO: Extend app UI with more Jetpack Compose UI elements here

    }
  }
}

@Composable
fun Greeting(name: String, modifier: Modifier = Modifier) {
  Text(
    text = "Hello $name !",
    modifier = modifier.padding(16.dp, 16.dp),
    style = MaterialTheme.typography.bodyLarge
  )
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
fun MainScreenPreview() {
  ADASmartAlarmTheme { MainScreen(listOf("Android")) }
}

