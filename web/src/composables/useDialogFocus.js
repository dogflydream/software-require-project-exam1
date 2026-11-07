import { onMounted, onUnmounted, nextTick } from 'vue'

// Keep keyboard focus inside the topmost dialog and restore the trigger on exit.
const dialogs = []
let previousOverflow = ''
export function useDialogFocus(element, onClose) {
  let trigger
  function keydown(event) {
    if (dialogs.at(-1) !== element) return
    if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); onClose(); return }
    if (event.key !== 'Tab' || !element.value) return
    const controls = [...element.value.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], [tabindex="0"]')].filter(el => el.getClientRects().length)
    const first = controls[0], last = controls.at(-1)
    if (!first) { event.preventDefault(); element.value.focus(); return }
    if (event.shiftKey && (document.activeElement === first || !element.value.contains(document.activeElement))) { event.preventDefault(); last.focus() }
    else if (!event.shiftKey && (document.activeElement === last || !element.value.contains(document.activeElement))) { event.preventDefault(); first.focus() }
  }
  onMounted(async () => {
    trigger = document.activeElement
    if (!dialogs.length) { previousOverflow = document.body.style.overflow; document.body.style.overflow = 'hidden' }
    dialogs.push(element)
    document.addEventListener('keydown', keydown)
    await nextTick()
    const initial = element.value?.querySelector('[data-initial-focus]') || element.value?.querySelector('input, button')
    initial?.focus()
  })
  onUnmounted(() => {
    document.removeEventListener('keydown', keydown)
    const index = dialogs.indexOf(element)
    const wasTop = index === dialogs.length - 1
    if (index !== -1) dialogs.splice(index, 1)
    if (!dialogs.length) document.body.style.overflow = previousOverflow
    if (wasTop && trigger?.isConnected) trigger.focus()
  })
}
