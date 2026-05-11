import '@testing-library/jest-dom/vitest';

class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver = ResizeObserver as unknown as typeof globalThis.ResizeObserver;
globalThis.DOMMatrixReadOnly = class DOMMatrixReadOnly {
  m22 = 1;
} as unknown as typeof globalThis.DOMMatrixReadOnly;

Object.defineProperties(HTMLElement.prototype, {
  offsetHeight: { get() { return 100; } },
  offsetWidth: { get() { return 180; } },
});

Object.defineProperty(SVGElement.prototype, 'getBBox', {
  value: () =>
    ({
      x: 0,
      y: 0,
      width: 0,
      height: 0,
    }) as DOMRect,
});
