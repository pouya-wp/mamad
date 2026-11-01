// Sales authorization stays independent of the panel's browser cookies.
function createSalesApi({ getToken, call }) {
  let token;
  return {
    async boot() {
      token = await getToken();
      const result = await call('device_boot', token, {});
      if (!result?.ready) throw new Error('مجوز همگام‌سازی دستگاه برقرار نشد.');
      return result;
    },
    async post(method, data) {
      if (method === 'sync_products') return { created: [], existing: [], disabled: true };
      if (method !== 'import_sales') throw new Error('این عملیات برای همگام‌سازی دستگاه مجاز نیست.');
      if (!token) throw new Error('ابتدا ثبت و بررسی دستگاه لازم است.');
      return call('device_import_sales', token, data);
    },
  };
}

module.exports = { createSalesApi };
