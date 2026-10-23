"""Check the locally served inline preview at desktop and narrow widths."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8767/')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 780, 'height': 1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url)
        frame = page.frame_locator('iframe')
        frame.locator('[data-panel="range-x"] svg').wait_for(timeout=20000)
        assert frame.locator('svg').count() == 9
        for profile in ('healthy', 'broad', 'individual', 'average'):
            frame.locator('#vectrex-profile').select_option(profile)
            assert frame.locator('[data-panel="output-x"] svg circle').count() >= 8
        for controller in ('0', '1', '2', '3', '4'):
            frame.locator('#vectrex-controller').select_option(controller)
            assert (f'Aftermarket #{int(controller)-2}' if int(controller) >= 3 else f'Stock #{int(controller)+1}') in frame.locator('#vectrex-hold-values').inner_text()
        frame.locator('#vectrex-controller').select_option('2')
        frame.locator('#vectrex-hold').select_option('right')
        frame.locator('#vectrex-hold').select_option('left')
        for name in ('hold-x', 'hold-y', 'perimeter'):
            assert frame.locator(f'[data-panel="{name}"] svg path[d]').count() >= 3
        page.wait_for_timeout(350)
        page.screenshot(path=args.output, full_page=True)
        frame.locator('[data-panel="perimeter"] svg').scroll_into_view_if_needed()
        page.wait_for_timeout(350)
        page.screenshot(path=str(Path(args.output).with_name('vectrex-comparison-raw.png')))
        dimensions = []
        for width in (780, 360, 320):
            page.set_viewport_size({'width': width, 'height': 1000})
            page.wait_for_timeout(400)
            inner = page.frames[1]
            size = inner.evaluate('({width: innerWidth, scroll: document.documentElement.scrollWidth, charts: document.querySelectorAll("svg").length})')
            dimensions.append(size)
            assert size['scroll'] <= size['width'] + 1, size
        page.screenshot(path=str(Path(args.output).with_name('vectrex-comparison-narrow.png')), full_page=True)
        assert not errors, errors
        print(json.dumps({'chart_count': 9, 'profiles_and_recording_controls': 'passed', 'responsive_checks': dimensions, 'js_errors': errors}, indent=2))
        browser.close()


if __name__ == '__main__':
    main()
