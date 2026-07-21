// Minimal toast bus: any module can push a toast; ToastHost renders them.
let listeners = []
let counter = 0

export function subscribeToasts(fn) {
  listeners.push(fn)
  return () => { listeners = listeners.filter((l) => l !== fn) }
}

export function toast(message, kind = 'error') {
  const item = { id: ++counter, message: String(message), kind }
  listeners.forEach((fn) => fn(item))
  return item.id
}
