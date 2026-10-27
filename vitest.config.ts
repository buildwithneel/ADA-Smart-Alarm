import path from "path";

export default {
  resolve: {
    alias: {
      "@ada/shared": path.resolve(__dirname, "packages/shared/src/index.ts"),
      axios: path.resolve(__dirname, "frontend/node_modules/axios"),
      "react-native": path.resolve(__dirname, "apps/mobile/src/__mocks__/react-native.ts"),
    },
  },
  test: {
    environment: "node",
  },
};
