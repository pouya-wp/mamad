/**
 * The café as it really is: menu, prices, recipes, ingredients and suppliers
 * exported from the live ERPNext site, frozen here so the demo build needs no backend.
 * Money is in Rial, the way the backend keeps it.
 */
type Recipe = { item_code: string; item_name: string; qty: number; uom: string; rate: number }

export type Dataset = {
  groups: { menu: string[]; ingredients: string[] }
  menu: { item_code: string; item_name: string; item_group: string; rate: number; description: string | null }[]
  ingredients: { item_code: string; item_name: string; item_group: string; stock_uom: string; safety_stock: number; valuation_rate: number; actual_qty: number }[]
  recipes: Record<string, Recipe[]>
  suppliers: { name: string; supplier_name: string; mobile_no: string | null }[]
  accounts: { name: string; account_name: string }[]
}

export const DATASET: Dataset = {
  "groups": {
    "menu": [
      "غذا و میان‌وعده",
      "کیک و دسر",
      "نوشیدنی سرد",
      "نوشیدنی گرم"
    ],
    "ingredients": [
      "مواد اولیه",
      "بسته‌بندی و مصرفی"
    ]
  },
  "menu": [
    {
      "item_code": "املت",
      "item_name": "املت",
      "item_group": "غذا و میان‌وعده",
      "description": null,
      "rate": 2100000.0
    },
    {
      "item_code": "پیتزا پپرونی",
      "item_name": "پیتزا پپرونی",
      "item_group": "غذا و میان‌وعده",
      "description": null,
      "rate": 4200000.0
    },
    {
      "item_code": "پیتزا مارگاریتا",
      "item_name": "پیتزا مارگاریتا",
      "item_group": "غذا و میان‌وعده",
      "description": null,
      "rate": 3600000.0
    },
    {
      "item_code": "صبحانه انگلیسی",
      "item_name": "صبحانه انگلیسی",
      "item_group": "غذا و میان‌وعده",
      "description": null,
      "rate": 3200000.0
    },
    {
      "item_code": "چیزکیک",
      "item_name": "چیزکیک",
      "item_group": "کیک و دسر",
      "description": null,
      "rate": 1600000.0
    },
    {
      "item_code": "کیک شکلاتی",
      "item_name": "کیک شکلاتی",
      "item_group": "کیک و دسر",
      "description": null,
      "rate": 1400000.0
    },
    {
      "item_code": "آیس آمریکانو",
      "item_name": "آیس آمریکانو",
      "item_group": "نوشیدنی سرد",
      "description": null,
      "rate": 1200000.0
    },
    {
      "item_code": "آیس لاته",
      "item_name": "آیس لاته",
      "item_group": "نوشیدنی سرد",
      "description": null,
      "rate": 1550000.0
    },
    {
      "item_code": "آیس وانیل کافه",
      "item_name": "آیس وانیل کافه",
      "item_group": "نوشیدنی سرد",
      "description": null,
      "rate": 1650000.0
    },
    {
      "item_code": "لیموناد",
      "item_name": "لیموناد",
      "item_group": "نوشیدنی سرد",
      "description": null,
      "rate": 1300000.0
    },
    {
      "item_code": "موهیتو",
      "item_name": "موهیتو",
      "item_group": "نوشیدنی سرد",
      "description": null,
      "rate": 1500000.0
    },
    {
      "item_code": "آمریکانو",
      "item_name": "آمریکانو",
      "item_group": "نوشیدنی گرم",
      "description": null,
      "rate": 1100000.0
    },
    {
      "item_code": "اسپرسو",
      "item_name": "اسپرسو",
      "item_group": "نوشیدنی گرم",
      "description": null,
      "rate": 950000.0
    },
    {
      "item_code": "دمی V60",
      "item_name": "دمی V60",
      "item_group": "نوشیدنی گرم",
      "description": null,
      "rate": 1500000.0
    },
    {
      "item_code": "کاپوچینو",
      "item_name": "کاپوچینو",
      "item_group": "نوشیدنی گرم",
      "description": null,
      "rate": 1400000.0
    },
    {
      "item_code": "کارامل ماکیاتو",
      "item_name": "کارامل ماکیاتو",
      "item_group": "نوشیدنی گرم",
      "description": null,
      "rate": 1650000.0
    },
    {
      "item_code": "لاته",
      "item_name": "لاته",
      "item_group": "نوشیدنی گرم",
      "description": null,
      "rate": 1450000.0
    },
    {
      "item_code": "ماچا لاته",
      "item_name": "ماچا لاته",
      "item_group": "نوشیدنی گرم",
      "description": null,
      "rate": 1750000.0
    },
    {
      "item_code": "موکا",
      "item_name": "موکا",
      "item_group": "نوشیدنی گرم",
      "description": null,
      "rate": 1600000.0
    },
    {
      "item_code": "هات چاکلت",
      "item_name": "هات چاکلت",
      "item_group": "نوشیدنی گرم",
      "description": null,
      "rate": 1500000.0
    }
  ],
  "ingredients": [
    {
      "item_code": "جعبه پیتزا",
      "item_name": "جعبه پیتزا",
      "item_group": "بسته‌بندی و مصرفی",
      "stock_uom": "Nos",
      "safety_stock": 20.0,
      "actual_qty": 12.0,
      "valuation_rate": 45000.0
    },
    {
      "item_code": "لیوان کاغذی",
      "item_name": "لیوان کاغذی",
      "item_group": "بسته‌بندی و مصرفی",
      "stock_uom": "Nos",
      "safety_stock": 100.0,
      "actual_qty": 2099.0,
      "valuation_rate": 18000.0
    },
    {
      "item_code": "پپرونی",
      "item_name": "پپرونی",
      "item_group": "مواد اولیه",
      "stock_uom": "Gram",
      "safety_stock": 1000.0,
      "actual_qty": 8850.0,
      "valuation_rate": 14000.0
    },
    {
      "item_code": "پنیر موزارلا",
      "item_name": "پنیر موزارلا",
      "item_group": "مواد اولیه",
      "stock_uom": "Gram",
      "safety_stock": 2000.0,
      "actual_qty": 36750.0,
      "valuation_rate": 9500.0
    },
    {
      "item_code": "پودر شکلات",
      "item_name": "پودر شکلات",
      "item_group": "مواد اولیه",
      "stock_uom": "Gram",
      "safety_stock": 500.0,
      "actual_qty": 2890.0,
      "valuation_rate": 9000.0
    },
    {
      "item_code": "پودر ماچا",
      "item_name": "پودر ماچا",
      "item_group": "مواد اولیه",
      "stock_uom": "Gram",
      "safety_stock": 150.0,
      "actual_qty": 40.0,
      "valuation_rate": 61428.571464286
    },
    {
      "item_code": "تخم مرغ",
      "item_name": "تخم مرغ",
      "item_group": "مواد اولیه",
      "stock_uom": "Nos",
      "safety_stock": 30.0,
      "actual_qty": 584.0,
      "valuation_rate": 70000.0
    },
    {
      "item_code": "چیزکیک (برش)",
      "item_name": "چیزکیک (برش)",
      "item_group": "مواد اولیه",
      "stock_uom": "Nos",
      "safety_stock": 6.0,
      "actual_qty": 38.0,
      "valuation_rate": 520000.0
    },
    {
      "item_code": "خامه",
      "item_name": "خامه",
      "item_group": "مواد اولیه",
      "stock_uom": "Millilitre",
      "safety_stock": 1500.0,
      "actual_qty": 20180.0,
      "valuation_rate": 1600.0
    },
    {
      "item_code": "خمیر پیتزا",
      "item_name": "خمیر پیتزا",
      "item_group": "مواد اولیه",
      "stock_uom": "Nos",
      "safety_stock": 10.0,
      "actual_qty": 36.0,
      "valuation_rate": 180000.0
    },
    {
      "item_code": "دانه قهوه اسپرسو",
      "item_name": "دانه قهوه اسپرسو",
      "item_group": "مواد اولیه",
      "stock_uom": "Gram",
      "safety_stock": 2000.0,
      "actual_qty": 30866.0,
      "valuation_rate": 25000.0
    },
    {
      "item_code": "دانه قهوه دمی",
      "item_name": "دانه قهوه دمی",
      "item_group": "مواد اولیه",
      "stock_uom": "Gram",
      "safety_stock": 800.0,
      "actual_qty": 8610.0,
      "valuation_rate": 22000.0
    },
    {
      "item_code": "سس گوجه",
      "item_name": "سس گوجه",
      "item_group": "مواد اولیه",
      "stock_uom": "Gram",
      "safety_stock": 1000.0,
      "actual_qty": 4810.0,
      "valuation_rate": 2500.0
    },
    {
      "item_code": "سیروپ کارامل",
      "item_name": "سیروپ کارامل",
      "item_group": "مواد اولیه",
      "stock_uom": "Millilitre",
      "safety_stock": 500.0,
      "actual_qty": 300.0,
      "valuation_rate": 3858.974342735
    },
    {
      "item_code": "سیروپ وانیل",
      "item_name": "سیروپ وانیل",
      "item_group": "مواد اولیه",
      "stock_uom": "Millilitre",
      "safety_stock": 500.0,
      "actual_qty": 3320.0,
      "valuation_rate": 3500.0
    },
    {
      "item_code": "شکر",
      "item_name": "شکر",
      "item_group": "مواد اولیه",
      "stock_uom": "Gram",
      "safety_stock": 2000.0,
      "actual_qty": 12955.0,
      "valuation_rate": 450.0
    },
    {
      "item_code": "شیر",
      "item_name": "شیر",
      "item_group": "مواد اولیه",
      "stock_uom": "Millilitre",
      "safety_stock": 10000.0,
      "actual_qty": 229400.0,
      "valuation_rate": 695.640802092
    },
    {
      "item_code": "کره",
      "item_name": "کره",
      "item_group": "مواد اولیه",
      "stock_uom": "Gram",
      "safety_stock": 500.0,
      "actual_qty": 6625.0,
      "valuation_rate": 12000.0
    },
    {
      "item_code": "کیک شکلاتی (برش)",
      "item_name": "کیک شکلاتی (برش)",
      "item_group": "مواد اولیه",
      "stock_uom": "Nos",
      "safety_stock": 6.0,
      "actual_qty": 59.0,
      "valuation_rate": 450000.0
    },
    {
      "item_code": "لیمو تازه",
      "item_name": "لیمو تازه",
      "item_group": "مواد اولیه",
      "stock_uom": "Gram",
      "safety_stock": 1000.0,
      "actual_qty": 19680.0,
      "valuation_rate": 1500.0
    },
    {
      "item_code": "نان تست",
      "item_name": "نان تست",
      "item_group": "مواد اولیه",
      "stock_uom": "Nos",
      "safety_stock": 20.0,
      "actual_qty": 428.0,
      "valuation_rate": 25000.0
    },
    {
      "item_code": "نعناع تازه",
      "item_name": "نعناع تازه",
      "item_group": "مواد اولیه",
      "stock_uom": "Gram",
      "safety_stock": 200.0,
      "actual_qty": 2052.0,
      "valuation_rate": 4000.0
    },
    {
      "item_code": "یخ",
      "item_name": "یخ",
      "item_group": "مواد اولیه",
      "stock_uom": "Gram",
      "safety_stock": 5000.0,
      "actual_qty": 78110.0,
      "valuation_rate": 50.0
    }
  ],
  "recipes": {
    "املت": [
      {
        "item_code": "تخم مرغ",
        "item_name": "تخم مرغ",
        "qty": 3.0,
        "uom": "Nos",
        "rate": 70000.0
      },
      {
        "item_code": "سس گوجه",
        "item_name": "سس گوجه",
        "qty": 80.0,
        "uom": "Gram",
        "rate": 2500.0
      },
      {
        "item_code": "نان تست",
        "item_name": "نان تست",
        "qty": 1.0,
        "uom": "Nos",
        "rate": 25000.0
      }
    ],
    "پیتزا پپرونی": [
      {
        "item_code": "خمیر پیتزا",
        "item_name": "خمیر پیتزا",
        "qty": 1.0,
        "uom": "Nos",
        "rate": 180000.0
      },
      {
        "item_code": "پنیر موزارلا",
        "item_name": "پنیر موزارلا",
        "qty": 120.0,
        "uom": "Gram",
        "rate": 9500.0
      },
      {
        "item_code": "پپرونی",
        "item_name": "پپرونی",
        "qty": 70.0,
        "uom": "Gram",
        "rate": 14000.0
      },
      {
        "item_code": "سس گوجه",
        "item_name": "سس گوجه",
        "qty": 60.0,
        "uom": "Gram",
        "rate": 2500.0
      }
    ],
    "پیتزا مارگاریتا": [
      {
        "item_code": "خمیر پیتزا",
        "item_name": "خمیر پیتزا",
        "qty": 1.0,
        "uom": "Nos",
        "rate": 180000.0
      },
      {
        "item_code": "پنیر موزارلا",
        "item_name": "پنیر موزارلا",
        "qty": 150.0,
        "uom": "Gram",
        "rate": 9500.0
      },
      {
        "item_code": "سس گوجه",
        "item_name": "سس گوجه",
        "qty": 70.0,
        "uom": "Gram",
        "rate": 2500.0
      }
    ],
    "صبحانه انگلیسی": [
      {
        "item_code": "تخم مرغ",
        "item_name": "تخم مرغ",
        "qty": 2.0,
        "uom": "Nos",
        "rate": 70000.0
      },
      {
        "item_code": "نان تست",
        "item_name": "نان تست",
        "qty": 2.0,
        "uom": "Nos",
        "rate": 25000.0
      },
      {
        "item_code": "کره",
        "item_name": "کره",
        "qty": 15.0,
        "uom": "Gram",
        "rate": 12000.0
      }
    ],
    "چیزکیک": [
      {
        "item_code": "چیزکیک (برش)",
        "item_name": "چیزکیک (برش)",
        "qty": 1.0,
        "uom": "Nos",
        "rate": 520000.0
      }
    ],
    "کیک شکلاتی": [
      {
        "item_code": "کیک شکلاتی (برش)",
        "item_name": "کیک شکلاتی (برش)",
        "qty": 1.0,
        "uom": "Nos",
        "rate": 450000.0
      }
    ],
    "آیس آمریکانو": [
      {
        "item_code": "دانه قهوه اسپرسو",
        "item_name": "دانه قهوه اسپرسو",
        "qty": 18.0,
        "uom": "Gram",
        "rate": 25000.0
      },
      {
        "item_code": "یخ",
        "item_name": "یخ",
        "qty": 180.0,
        "uom": "Gram",
        "rate": 50.0
      }
    ],
    "آیس لاته": [
      {
        "item_code": "دانه قهوه اسپرسو",
        "item_name": "دانه قهوه اسپرسو",
        "qty": 18.0,
        "uom": "Gram",
        "rate": 25000.0
      },
      {
        "item_code": "شیر",
        "item_name": "شیر",
        "qty": 200.0,
        "uom": "Millilitre",
        "rate": 695.640802092
      },
      {
        "item_code": "یخ",
        "item_name": "یخ",
        "qty": 150.0,
        "uom": "Gram",
        "rate": 50.0
      }
    ],
    "آیس وانیل کافه": [
      {
        "item_code": "دانه قهوه اسپرسو",
        "item_name": "دانه قهوه اسپرسو",
        "qty": 18.0,
        "uom": "Gram",
        "rate": 25000.0
      },
      {
        "item_code": "شیر",
        "item_name": "شیر",
        "qty": 180.0,
        "uom": "Millilitre",
        "rate": 695.640802092
      },
      {
        "item_code": "سیروپ وانیل",
        "item_name": "سیروپ وانیل",
        "qty": 20.0,
        "uom": "Millilitre",
        "rate": 3500.0
      },
      {
        "item_code": "یخ",
        "item_name": "یخ",
        "qty": 150.0,
        "uom": "Gram",
        "rate": 50.0
      }
    ],
    "لیموناد": [
      {
        "item_code": "لیمو تازه",
        "item_name": "لیمو تازه",
        "qty": 80.0,
        "uom": "Gram",
        "rate": 1500.0
      },
      {
        "item_code": "شکر",
        "item_name": "شکر",
        "qty": 25.0,
        "uom": "Gram",
        "rate": 450.0
      },
      {
        "item_code": "یخ",
        "item_name": "یخ",
        "qty": 180.0,
        "uom": "Gram",
        "rate": 50.0
      }
    ],
    "موهیتو": [
      {
        "item_code": "لیمو تازه",
        "item_name": "لیمو تازه",
        "qty": 60.0,
        "uom": "Gram",
        "rate": 1500.0
      },
      {
        "item_code": "نعناع تازه",
        "item_name": "نعناع تازه",
        "qty": 8.0,
        "uom": "Gram",
        "rate": 4000.0
      },
      {
        "item_code": "شکر",
        "item_name": "شکر",
        "qty": 20.0,
        "uom": "Gram",
        "rate": 450.0
      },
      {
        "item_code": "یخ",
        "item_name": "یخ",
        "qty": 200.0,
        "uom": "Gram",
        "rate": 50.0
      }
    ],
    "آمریکانو": [
      {
        "item_code": "دانه قهوه اسپرسو",
        "item_name": "دانه قهوه اسپرسو",
        "qty": 18.0,
        "uom": "Gram",
        "rate": 25000.0
      }
    ],
    "اسپرسو": [
      {
        "item_code": "دانه قهوه اسپرسو",
        "item_name": "دانه قهوه اسپرسو",
        "qty": 18.0,
        "uom": "Gram",
        "rate": 25000.0
      }
    ],
    "دمی V60": [
      {
        "item_code": "دانه قهوه دمی",
        "item_name": "دانه قهوه دمی",
        "qty": 15.0,
        "uom": "Gram",
        "rate": 22000.0
      }
    ],
    "کاپوچینو": [
      {
        "item_code": "دانه قهوه اسپرسو",
        "item_name": "دانه قهوه اسپرسو",
        "qty": 18.0,
        "uom": "Gram",
        "rate": 25000.0
      },
      {
        "item_code": "شیر",
        "item_name": "شیر",
        "qty": 160.0,
        "uom": "Millilitre",
        "rate": 695.640802092
      }
    ],
    "کارامل ماکیاتو": [
      {
        "item_code": "دانه قهوه اسپرسو",
        "item_name": "دانه قهوه اسپرسو",
        "qty": 18.0,
        "uom": "Gram",
        "rate": 25000.0
      },
      {
        "item_code": "شیر",
        "item_name": "شیر",
        "qty": 200.0,
        "uom": "Millilitre",
        "rate": 695.640802092
      },
      {
        "item_code": "سیروپ کارامل",
        "item_name": "سیروپ کارامل",
        "qty": 20.0,
        "uom": "Millilitre",
        "rate": 3858.974342735
      }
    ],
    "لاته": [
      {
        "item_code": "دانه قهوه اسپرسو",
        "item_name": "دانه قهوه اسپرسو",
        "qty": 18.0,
        "uom": "Gram",
        "rate": 25000.0
      },
      {
        "item_code": "شیر",
        "item_name": "شیر",
        "qty": 220.0,
        "uom": "Millilitre",
        "rate": 695.640802092
      }
    ],
    "ماچا لاته": [
      {
        "item_code": "پودر ماچا",
        "item_name": "پودر ماچا",
        "qty": 4.0,
        "uom": "Gram",
        "rate": 61428.571464286
      },
      {
        "item_code": "شیر",
        "item_name": "شیر",
        "qty": 220.0,
        "uom": "Millilitre",
        "rate": 695.640802092
      }
    ],
    "موکا": [
      {
        "item_code": "دانه قهوه اسپرسو",
        "item_name": "دانه قهوه اسپرسو",
        "qty": 18.0,
        "uom": "Gram",
        "rate": 25000.0
      },
      {
        "item_code": "شیر",
        "item_name": "شیر",
        "qty": 180.0,
        "uom": "Millilitre",
        "rate": 695.640802092
      },
      {
        "item_code": "پودر شکلات",
        "item_name": "پودر شکلات",
        "qty": 20.0,
        "uom": "Gram",
        "rate": 9000.0
      }
    ],
    "هات چاکلت": [
      {
        "item_code": "پودر شکلات",
        "item_name": "پودر شکلات",
        "qty": 30.0,
        "uom": "Gram",
        "rate": 9000.0
      },
      {
        "item_code": "شیر",
        "item_name": "شیر",
        "qty": 220.0,
        "uom": "Millilitre",
        "rate": 695.640802092
      },
      {
        "item_code": "خامه",
        "item_name": "خامه",
        "qty": 20.0,
        "uom": "Millilitre",
        "rate": 1600.0
      }
    ]
  },
  "suppliers": [
    {
      "name": "پخش مواد غذایی فرساد",
      "supplier_name": "پخش مواد غذایی فرساد",
      "mobile_no": "09130000003"
    },
    {
      "name": "رست قهوه یزد",
      "supplier_name": "رست قهوه یزد",
      "mobile_no": "09130000001"
    },
    {
      "name": "لبنیات پگاه",
      "supplier_name": "لبنیات پگاه",
      "mobile_no": "09130000002"
    }
  ],
  "accounts": [
    {
      "name": "آب، برق و گاز - CO",
      "account_name": "آب، برق و گاز"
    },
    {
      "name": "اجاره - CO",
      "account_name": "اجاره"
    },
    {
      "name": "اینترنت و تلفن - CO",
      "account_name": "اینترنت و تلفن"
    },
    {
      "name": "تبلیغات و بازاریابی - CO",
      "account_name": "تبلیغات و بازاریابی"
    },
    {
      "name": "تعمیرات و نگهداری - CO",
      "account_name": "تعمیرات و نگهداری"
    },
    {
      "name": "حقوق و دستمزد - CO",
      "account_name": "حقوق و دستمزد"
    },
    {
      "name": "سایر هزینه‌ها - CO",
      "account_name": "سایر هزینه‌ها"
    },
    {
      "name": "ملزومات و شوینده - CO",
      "account_name": "ملزومات و شوینده"
    }
  ]
}
