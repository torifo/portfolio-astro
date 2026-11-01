// 横に流れ続ける帯（トップの「これまでの旅」・作品ページの「公式の映像」「公式サイト」）。同じ並びを2周ぶん置き、端に近づいたら1周ぶん戻して途切れなく見せる。
// 左へ流す（右へ流すと逆に感じた）。マウスを乗せている間・触った直後・画面の外では止め、「動きを減らす」設定の人には流さない。
const SPEED = 36; // 1秒に動かす px（24 から本人の指示で1.5倍に）
const RESUME_DELAY = 2500; // 手で動かしたあと、流れを戻すまでの ms
const GAP = 16; // カードの間（gap-4）

export interface ReelOptions {
  /** 流れを止める／再開するボタン */
  toggle?: HTMLButtonElement | null;
  /** 前後に1枚ぶん送るボタン（data-step="-1" / "1"） */
  steps?: Iterable<HTMLButtonElement>;
  /** カード。マウスを乗せたカードに印（data-mouse-hover）を付け、CSS で浮かせる */
  card: string;
  /** 全部が収まって並べるだけになった（CSS が1周目を消した）ときと、帯に戻ったときに呼ぶ */
  onStill?: (still: boolean) => void;
}

/** 帯を動かす。同じ帯に二重には付けない。帯に data-reel-hold が付いている間（動画の再生中など）は流さない */
export function setupReel(reel: HTMLElement, { toggle = null, steps = [], card, onStill }: ReelOptions): void {
  if (reel.dataset.ready) return;
  const sets = reel.querySelectorAll<HTMLElement>('[data-reel-set]');
  if (sets.length < 2) return;
  reel.dataset.ready = '1';

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');

  // 1周の長さ（2周目の先頭 - 1周目の先頭。間の余白を含む）
  const period = () => sets[1].offsetLeft - sets[0].offsetLeft;
  const inset = () => sets[0].offsetLeft;
  // 1周の4分の1より左、または1と4分の1周より右へ出たら、1周ぶん戻す。見えている絵は同じなので気づかれない
  const wrap = (value: number) => {
    const p = period();
    if (p <= 0) return value;
    if (value < p * 0.25) return value + p;
    if (value >= p * 1.25) return value - p;
    return value;
  };

  // 2周目（読み上げの対象のほう）の先頭から始める
  let pos = sets[1].offsetLeft - inset();
  let target: number | null = null;
  let last = 0;
  let visible = true;
  let hovering = false;
  let still = false;
  let holdUntil = 0;
  let stopped = reduce.matches;
  reel.scrollLeft = pos;

  // 並べるだけのとき（1周目が消えている）は流さない
  new ResizeObserver(() => {
    const now = getComputedStyle(sets[0]).display === 'none';
    if (now === still) return;
    still = now;
    onStill?.(still);
  }).observe(reel);

  const render = () => {
    if (!toggle) return;
    toggle.setAttribute('aria-label', stopped ? '流れを再開する' : '流れを止める');
    toggle.querySelector('.reel-icon-pause')?.classList.toggle('hidden', stopped);
    toggle.querySelector('.reel-icon-play')?.classList.toggle('hidden', !stopped);
  };
  render();

  const tick = (now: number) => {
    if (!reel.isConnected) return; // ページを移ったら止める
    const dt = last ? Math.min(now - last, 100) : 0;
    last = now;
    if (target !== null) {
      // 前後のボタンで1枚ぶん送るときは、目標へなめらかに寄せる
      const before = pos;
      pos += (target - pos) * Math.min(1, dt / 120);
      if (Math.abs(target - pos) < 0.5) {
        pos = target;
        target = null;
      }
      const wrapped = wrap(pos);
      if (target !== null) target += wrapped - pos;
      pos = wrapped;
      if (pos !== before) reel.scrollLeft = pos;
    } else if (!stopped && !still && visible && !hovering && now >= holdUntil && !reel.hasAttribute('data-reel-hold')) {
      pos = wrap(pos + (SPEED * dt) / 1000);
      reel.scrollLeft = pos;
    }
    requestAnimationFrame(tick);
  };

  // 手で動かしたら、その位置を引き継ぐ（流している間の差は1px未満なので、2px を超えたら手で動かしたとみなす）
  reel.addEventListener(
    'scroll',
    () => {
      if (target !== null || Math.abs(reel.scrollLeft - pos) <= 2) return;
      pos = reel.scrollLeft;
      const wrapped = wrap(pos);
      if (wrapped !== pos) {
        pos = wrapped;
        reel.scrollLeft = pos;
      }
    },
    { passive: true },
  );
  const pause = () => {
    holdUntil = performance.now() + RESUME_DELAY;
  };
  reel.addEventListener('pointerenter', (event) => {
    if (event.pointerType === 'mouse') hovering = true;
  });
  // マウスで乗せたカードにだけ印を付ける（CSS で浮かせる）。指で触ったときは付けない
  reel.addEventListener('pointerover', (event) => {
    if (event.pointerType !== 'mouse') return;
    (event.target as Element).closest(card)?.setAttribute('data-mouse-hover', '');
  });
  reel.addEventListener('pointerout', (event) => {
    const hovered = (event.target as Element).closest(card);
    if (hovered && !hovered.contains(event.relatedTarget as Node | null)) hovered.removeAttribute('data-mouse-hover');
  });
  reel.addEventListener('pointerleave', () => {
    hovering = false;
  });
  reel.addEventListener('pointerdown', pause);
  reel.addEventListener('touchmove', pause, { passive: true });
  reel.addEventListener('wheel', pause, { passive: true });
  reel.addEventListener('focusin', () => {
    hovering = true;
  });
  reel.addEventListener('focusout', () => {
    hovering = false;
  });
  new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
  }).observe(reel);

  toggle?.addEventListener('click', () => {
    stopped = !stopped;
    render();
  });
  reduce.addEventListener('change', () => {
    stopped = reduce.matches;
    render();
  });
  for (const button of steps) {
    button.addEventListener('click', () => {
      const first = sets[1].firstElementChild as HTMLElement | null;
      const step = (first?.offsetWidth ?? 300) + GAP;
      const base = target ?? pos;
      pause();
      if (reduce.matches) {
        pos = wrap(base + step * Number(button.dataset.step));
        reel.scrollLeft = pos;
      } else {
        target = base + step * Number(button.dataset.step);
      }
    });
  }

  requestAnimationFrame(tick);
}
