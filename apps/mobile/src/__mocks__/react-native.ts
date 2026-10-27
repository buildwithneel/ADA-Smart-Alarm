export const Platform = {
  OS: "ios",
  select: (objs: any) => objs.ios ?? objs.default,
};

export const Linking = {
  openSettings: async () => {},
  openURL: async () => {},
};

export const Alert = {
  alert: () => {},
};

export const StyleSheet = {
  create: (styles: any) => styles,
};

export const View = "View";
export const Text = "Text";
export const TouchableOpacity = "TouchableOpacity";
export const ScrollView = "ScrollView";
export const TextInput = "TextInput";
export const Switch = "Switch";
export const ActivityIndicator = "ActivityIndicator";
export const FlatList = "FlatList";
export const RefreshControl = "RefreshControl";
export const SafeAreaView = "SafeAreaView";
export const StatusBar = "StatusBar";
