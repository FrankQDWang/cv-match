import './styles.css';

import { createHttpApi } from './api';
import { createApp } from './app';

const root = document.querySelector<HTMLDivElement>('#app');

if (!root) {
  throw new Error('App root not found.');
}

createApp(root, createHttpApi());
