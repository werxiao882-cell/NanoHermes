# Zhihu Anti-Bot Notes

## Error signatures
| Method | Response | Error Code |
|--------|----------|------------|
| curl to article page | 584-byte HTML with `zh-zse-ck` meta tag + JS challenge | - |
| browser_navigate | `{"error":{"code":40362,"message":"您当前请求存在异常..."}}` | 40362 |
| API `/api/v4/articles/ID` | `{"error":{"code":10003,"message":"请求参数异常..."}}` | 10003 |
| API `/api/v4/articles/ID/share` | Works (returns share templates) | - |
| Mobile UA curl | Same 584-byte block | - |
| With cookies from zhihu.com home | API still 403 | - |

## What DOES work
- Share API: `GET /api/v4/articles/{id}/share` returns share templates (weixin_url, sina_text with article title embedded)
- This can at least extract the article title from the `sina` template text

## What does NOT work
- Direct page access (any method)
- API article fetch (any endpoint)
- Browser-based fetch (blocked before page renders)
- Google/Bing cache of the page
- Web archive (archive.is, web.archive.org)
- Third-party zhihu extractors
- Sogou/Baidu search for specific article

## Conclusion
No automated method currently works for extracting full Zhihu article content. User must manually copy-paste or provide alternative source.
