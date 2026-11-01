package one.cafe.buying;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * The panel in a window, nothing more: one activity, one WebView, no libraries.
 * The purchase manager signs in once and the cookie keeps them signed in; whatever
 * the panel decides they may see is what they get, so this app has no rules of its own.
 */
public class MainActivity extends Activity {
	private static final String PANEL = "https://onecafe.beyondex.one";
	private static final String HOST = "onecafe.beyondex.one";
	private static final int PICK_FILE = 1;

	/** Shown when the phone cannot reach the panel at all. */
	private static final String OFFLINE =
		"<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'>"
		+ "<meta name='viewport' content='width=device-width,initial-scale=1'></head>"
		+ "<body style='margin:0;height:100vh;display:grid;place-items:center;background:#000;color:#f5f2ec;"
		+ "font-family:sans-serif;text-align:center'><div><p style='font-size:17px'>به پنل وصل نشد</p>"
		+ "<p style='color:#9d9da6;font-size:14px'>اینترنت گوشی را چک کن.</p>"
		+ "<a href='" + PANEL + "/' style='display:inline-block;margin-top:18px;padding:10px 22px;border-radius:12px;"
		+ "background:#ff4f1a;color:#fff;text-decoration:none'>تلاش دوباره</a></div></body></html>";

	private WebView web;
	private ValueCallback<Uri[]> pendingFiles;

	@Override
	protected void onCreate(Bundle state) {
		super.onCreate(state);
		web = new WebView(this);
		web.setBackgroundColor(0xFF000000);
		web.setLayoutParams(new ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
		setContentView(web);

		WebSettings settings = web.getSettings();
		settings.setJavaScriptEnabled(true);
		settings.setDomStorageEnabled(true);
		settings.setDatabaseEnabled(true);
		settings.setUseWideViewPort(true);
		settings.setLoadWithOverviewMode(true);
		settings.setSupportZoom(false);

		CookieManager cookies = CookieManager.getInstance();
		cookies.setAcceptCookie(true);
		cookies.setAcceptThirdPartyCookies(web, true);

		web.setWebViewClient(new WebViewClient() {
			@Override
			public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
				Uri url = request.getUrl();
				if (HOST.equals(url.getHost())) return false;
				// anything outside the panel belongs to the phone's browser
				try {
					startActivity(new Intent(Intent.ACTION_VIEW, url));
				} catch (Exception ignored) {
					// no browser on the phone: stay where we are
				}
				return true;
			}

			@Override
			public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
				if (request.isForMainFrame()) view.loadDataWithBaseURL(PANEL, OFFLINE, "text/html", "UTF-8", null);
			}
		});

		// invoice photos: let the panel open the phone's picker and camera
		web.setWebChromeClient(new WebChromeClient() {
			@Override
			public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
				if (pendingFiles != null) pendingFiles.onReceiveValue(null);
				pendingFiles = callback;
				try {
					startActivityForResult(params.createIntent(), PICK_FILE);
					return true;
				} catch (Exception problem) {
					pendingFiles = null;
					return false;
				}
			}
		});

		if (state != null) web.restoreState(state);
		else web.loadUrl(PANEL + "/");
	}

	@Override
	protected void onActivityResult(int request, int result, Intent data) {
		if (request != PICK_FILE) {
			super.onActivityResult(request, result, data);
			return;
		}
		if (pendingFiles == null) return;
		pendingFiles.onReceiveValue(FileChooserParamsCompat.parse(result, data));
		pendingFiles = null;
	}

	/** The one bit of plumbing a library would have done for us. */
	private static final class FileChooserParamsCompat {
		static Uri[] parse(int result, Intent data) {
			if (result != RESULT_OK || data == null) return null;
			if (data.getClipData() != null) {
				int count = data.getClipData().getItemCount();
				Uri[] files = new Uri[count];
				for (int i = 0; i < count; i++) files[i] = data.getClipData().getItemAt(i).getUri();
				return files;
			}
			return data.getData() == null ? null : new Uri[] { data.getData() };
		}
	}

	@Override
	public boolean onKeyDown(int code, KeyEvent event) {
		if (code == KeyEvent.KEYCODE_BACK && web.canGoBack()) {
			web.goBack();
			return true;
		}
		return super.onKeyDown(code, event);
	}

	@Override
	protected void onSaveInstanceState(Bundle state) {
		super.onSaveInstanceState(state);
		web.saveState(state);
	}

	@Override
	protected void onPause() {
		super.onPause();
		// keep the session on disk, so the buyer signs in once and not every morning
		CookieManager.getInstance().flush();
	}
}
