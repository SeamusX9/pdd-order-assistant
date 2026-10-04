# -*- coding: utf-8 -*-
"""
平台适配器层
每个适配器: match(url) / display_name / fields / scroll_selector / extract_js
统一字段 schema: shop 店铺名, name 商品名, spec 规格, price 单价, qty 数量,
                 paid 实付金额, status 订单状态, img 缩略图URL
"""

# ============ 拼多多（已验证 2026-08，data-test 属性稳定） ============
PDD_EXTRACT_JS = r"""
() => {
    const cards = document.querySelectorAll('[data-test="店铺名称"]');
    const results = [];
    for (const shopEl of cards) {
        const card = shopEl.closest('.U6SAh0Eo');
        if (!card) continue;
        const shop = (shopEl.innerText || '').trim();
        const statusEl = card.querySelector('[data-test="订单状态"]');
        const status = (statusEl ? statusEl.innerText : '').replace(/\s+/g, ' ').trim();
        let paid = '';
        const paidEl = card.querySelector('.pdcOje4N');
        if (paidEl) {
            paid = (paidEl.innerText || '').replace(/\s+/g, '').replace(/[￥¥]/g, '');
        }
        const goodsRows = card.querySelectorAll('.bH7cbEvO');
        for (const g of goodsRows) {
            const nameEl = g.querySelector('[data-test="商品名称"]');
            const name = (nameEl ? nameEl.innerText : '').replace(/\s+/g, ' ').trim();
            const specEl = g.querySelector('.bJrhQPD0');
            const spec = (specEl ? specEl.innerText : '').replace(/\s+/g, ' ').trim();
            const priceEl = g.querySelector('[data-test="商品价格"]');
            const price = (priceEl ? priceEl.innerText : '').replace(/\s+/g, '').replace(/[￥¥]/g, '');
            const qtyEl = g.querySelector('.r6qvgq4W');
            const qtyText = (qtyEl ? qtyEl.innerText : '').replace(/\s+/g, '');
            const qty = qtyText.replace(/[x×X]/g, '');
            const imgEl = g.querySelector('[data-test="商品图片"] img');
            const imgSrc = imgEl ? (imgEl.currentSrc || imgEl.src || '') : '';
            results.push({ shop, status, name, spec, price, qty, paid, img: imgSrc });
        }
    }
    return results;
}
"""

# ============ 通用启发式（淘宝/京东等未适配平台兜底，实验性） ============
GENERIC_EXTRACT_JS = r"""
() => {
    const results = [];
    const seen = new Set();
    // 找出所有含商品图片的"行"：img 尺寸 50~400px，src 含常见图床域名
    const imgs = Array.from(document.querySelectorAll('img')).filter(im => {
        const src = im.currentSrc || im.src || '';
        if (!/^(https?:)?\/\//.test(src)) return false;
        const w = im.naturalWidth || im.width || 0;
        const h = im.naturalHeight || im.height || 0;
        if (w > 0 && (w < 40 || w > 600)) return false;
        return true;
    });
    for (const im of imgs) {
        // 向上找含价格文本的最小容器
        let el = im.parentElement;
        let row = null;
        for (let i = 0; i < 6 && el; i++) {
            const txt = el.innerText || '';
            if (/[¥￥]\s*\d+\.?\d*|\d+\.\d{2}/.test(txt)) { row = el; break; }
            el = el.parentElement;
        }
        if (!row || seen.has(row)) continue;
        seen.add(row);
        const txt = (row.innerText || '').replace(/\s+/g, ' ').trim();
        const priceM = txt.match(/[¥￥]\s*(\d+\.?\d*)/);
        const qtyM = txt.match(/[x×]\s*(\d+)/);
        const nameM = txt.match(/([\u4e00-\u9fa5A-Za-z0-9][\u4e00-\u9fa5A-Za-z0-9 ｜|·&（）()【】\[\]a-zA-Z0-9+/\-]{5,}?)(?=\s*[¥￥])/);
        results.push({
            shop: '', name: nameM ? nameM[1].trim() : (txt.slice(0, 40) || ''),
            spec: '', price: priceM ? priceM[1] : '',
            qty: qtyM ? qtyM[1] : '1',
            paid: priceM ? priceM[1] : '',
            status: '', img: im.currentSrc || im.src || ''
        });
    }
    return results;
}
"""


class PinduoduoAdapter:
    name = "拼多多订单"
    def match(self, url):
        return "pinduoduo.com" in url
    @property
    def fields(self):
        return ["shop", "name", "spec", "price", "qty", "paid", "status", "img"]
    @property
    def scroll_selector(self):
        return '[data-test="店铺名称"]'
    @property
    def extract_js(self):
        return PDD_EXTRACT_JS
    def count_js(self):
        return 'document.querySelectorAll(\'[data-test="店铺名称"]\').length'
    def count_loaded(self, n):
        return n  # 店铺数 ≈ 商品记录数（单商品订单），多商品订单按行算


class GenericAdapter:
    name = "通用启发式(实验性)"
    def match(self, url):
        return True  # 兜底
    @property
    def fields(self):
        return ["name", "price", "qty", "img"]
    @property
    def scroll_selector(self):
        return "img"  # 计数不可靠，滚动时用页面高度判断
    @property
    def extract_js(self):
        return GENERIC_EXTRACT_JS
    def count_js(self):
        return "document.body.scrollHeight"
    def count_loaded(self, n):
        return 0


def get_adapter(url):
    """按 URL 匹配适配器，找不到用通用兜底"""
    for cls in (PinduoduoAdapter, GenericAdapter):
        a = cls()
        if a.match(url):
            return a
    return GenericAdapter()


FIELD_LABELS = {
    "shop": "店铺名", "name": "商品名", "spec": "规格",
    "price": "单价", "qty": "数量", "paid": "实付金额",
    "status": "订单状态", "img": "商品缩略图",
}

# 图片下载 URL 改写规则（各平台可定制）
def rewrite_img_url(url, platform):
    if "pddpic.com" in url:
        import re
        clean = re.sub(r'\?imageMogr2/.*$', '', url)
        return clean + '?imageMogr2/format/jpg/thumbnail/120x'
    return url
