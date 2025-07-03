import solid from 'vite-plugin-solid';

export default {
  plugins: [solid()],
  build: {
    target: 'esnext',
    polyfillDynamicImport: false,
  },
};



