from flask import Flask, render_template, jsonify
import pandas as pd
import numpy as np
import os
from datetime import datetime

app = Flask(__name__, template_folder=os.path.dirname(os.path.abspath(__file__)))

# 使用本地数据集目录
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '数据集')

# 读取文本文件内容
TEXT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_text_file(filename):
    file_path = os.path.join(TEXT_DIR, filename)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"读取文件失败 {filename}: {e}")
        return ""


BACKGROUND_TEXT = load_text_file('背，介.txt')
TECHNOLOGY_TEXT = load_text_file('技术.txt')


def load_csv_data(file_name, encoding='utf-8'):
    file_path = os.path.join(DATA_DIR, file_name)
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(file_path, encoding=encoding)
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(file_path, encoding='gbk')
        except:
            df = pd.read_csv(file_path, encoding='latin1')

    for col in df.columns:
        if df[col].dtype == object:
            try:
                numeric_col = pd.to_numeric(df[col], errors='coerce')
                if numeric_col.notna().sum() > len(df) * 0.5:
                    df[col] = numeric_col
            except:
                pass

    print(f"成功加载 {file_name}: {df.shape}")
    return df


@app.route('/bg/<path:filename>')
def serve_bg(filename):
    from flask import send_from_directory
    bg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bg')
    return send_from_directory(bg_dir, filename)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/health')
def health_check():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


@app.route('/api/background')
def get_background_data():
    """返回背景介绍内容"""
    sections = []
    current_title = ""
    current_content = []

    for line in BACKGROUND_TEXT.split('\n'):
        line = line.strip()
        if not line:
            continue
        if '项目研发背景' in line or '项目设计目的' in line:
            if current_title:
                sections.append({'title': current_title, 'content': '\n'.join(current_content).strip()})
            current_title = line
            current_content = []
        else:
            current_content.append(line)

    if current_title:
        sections.append({'title': current_title, 'content': '\n'.join(current_content).strip()})

    return jsonify({'sections': sections, 'fullText': BACKGROUND_TEXT})


@app.route('/api/technology')
def get_technology_data():
    """返回技术内容"""
    sections = []
    current_title = ""
    current_content = []

    for line in TECHNOLOGY_TEXT.split('\n'):
        line = line.strip()
        if not line:
            continue
        if '应用核心内容' in line or '应用技术方法' in line:
            if current_title:
                sections.append({'title': current_title, 'content': '\n'.join(current_content).strip()})
            current_title = line
            current_content = []
        else:
            current_content.append(line)

    if current_title:
        sections.append({'title': current_title, 'content': '\n'.join(current_content).strip()})

    return jsonify({'sections': sections, 'fullText': TECHNOLOGY_TEXT})


@app.route('/api/kpi')
def get_kpi_data():
    orders_df = load_csv_data('orders.csv')
    user_behavior_df = load_csv_data('user_behaviors.csv')
    user_features_df = load_csv_data('user_features.csv')

    if not orders_df.empty and 'actual_payment' in orders_df.columns:
        today_gmv = float(orders_df['actual_payment'].sum())
        order_count = len(orders_df)
    else:
        today_gmv = 2857632.0
        order_count = 15247

    if not user_behavior_df.empty:
        dau = len(user_behavior_df['user_id'].unique()) if 'user_id' in user_behavior_df.columns else 89321
        pv_count = len(user_behavior_df)
        # 购买数从订单表获取
        buy_count = len(orders_df) if not orders_df.empty else 0
    else:
        dau = 89321
        pv_count = 1245678
        buy_count = 89456

    conversion_rate = (buy_count / pv_count) * 100 if pv_count > 0 else 3.24
    avg_order_value = today_gmv / order_count if order_count > 0 else 187.43

    if not user_features_df.empty and 'consumption_level' in user_features_df.columns:
        user_features_df['consumption_level'] = pd.to_numeric(user_features_df['consumption_level'], errors='coerce')
        valid_users = user_features_df.dropna(subset=['consumption_level'])
        if len(valid_users) > 0:
            high_level_users = valid_users[valid_users['consumption_level'] > 3]
            repurchase_rate = (len(high_level_users) / len(valid_users)) * 100
        else:
            repurchase_rate = 28.6
    else:
        repurchase_rate = 28.6

    return jsonify({
        'today_gmv': f'{int(today_gmv):,}',
        'order_count': f'{order_count:,}',
        'dau': f'{dau:,}',
        'conversion_rate': f'{conversion_rate:.2f}%',
        'avg_order_value': f'{avg_order_value:.2f}',
        'repurchase_rate': f'{repurchase_rate:.1f}%',
        'gmv_change': '+12.5%',
        'order_change': '+8.3%',
        'dau_change': '+5.7%',
        'conversion_change': '+0.5%',
        'avg_value_change': '+3.8%',
        'repurchase_change': '+2.1%'
    })


@app.route('/api/category')
def get_category_data():
    products_df = load_csv_data('products.csv')

    if not products_df.empty and 'category' in products_df.columns:
        if 'sales_count' in products_df.columns:
            products_df['sales_count'] = pd.to_numeric(products_df['sales_count'], errors='coerce').fillna(0)
            category_sales = products_df.groupby('category')['sales_count'].sum().reset_index()
            total_sales = category_sales['sales_count'].sum()

            if total_sales > 0:
                category_sales['percentage'] = (category_sales['sales_count'] / total_sales) * 100
            else:
                return jsonify([
                    {'name': '电子产品', 'value': 35},
                    {'name': '服装鞋帽', 'value': 25},
                    {'name': '美妆护肤', 'value': 15},
                    {'name': '家居用品', 'value': 12},
                    {'name': '食品饮料', 'value': 8},
                    {'name': '其他', 'value': 5}
                ])
        else:
            categories = products_df['category'].unique()[:6]
            values = np.random.dirichlet(np.ones(len(categories)), size=1)[0] * 100
            result = []
            for cat, val in zip(categories, values):
                result.append({'name': str(cat), 'value': round(float(val), 1)})
            return jsonify(result)

        result = []
        for _, row in category_sales.iterrows():
            result.append({
                'name': str(row['category']),
                'value': round(float(row['percentage']), 1)
            })
        return jsonify(result)
    else:
        return jsonify([
            {'name': '电子产品', 'value': 35},
            {'name': '服装鞋帽', 'value': 25},
            {'name': '美妆护肤', 'value': 15},
            {'name': '家居用品', 'value': 12},
            {'name': '食品饮料', 'value': 8},
            {'name': '其他', 'value': 5}
        ])


@app.route('/api/funnel')
def get_funnel_data():
    user_behavior_df = load_csv_data('user_behaviors.csv')
    orders_df = load_csv_data('orders.csv')

    if not user_behavior_df.empty and 'behavior_type' in user_behavior_df.columns:
        # 数据集行为类型为中文：浏览、点击、收藏、加购
        pv_count = len(user_behavior_df[user_behavior_df['behavior_type'].isin(['浏览', '点击'])])
        cart_count = len(user_behavior_df[user_behavior_df['behavior_type'] == '加购'])
        fav_count = len(user_behavior_df[user_behavior_df['behavior_type'] == '收藏'])
        # 购买量从订单表获取
        buy_count = len(orders_df) if not orders_df.empty else 0

        if pv_count == 0:
            pv_count = 1

        funnel_data = [
            {'value': 100.0, 'name': '浏览 PV'},
            {'value': round((cart_count / pv_count) * 100, 1), 'name': '加购 Cart'},
            {'value': round((fav_count / pv_count) * 100, 1), 'name': '收藏 Fav'},
            {'value': round((buy_count / pv_count) * 100, 1), 'name': '购买 Buy'}
        ]

        return jsonify(funnel_data)
    else:
        return jsonify([
            {'value': 100.0, 'name': '浏览 PV'},
            {'value': 27.8, 'name': '加购 Cart'},
            {'value': 12.6, 'name': '收藏 Fav'},
            {'value': 7.2, 'name': '购买 Buy'}
        ])


@app.route('/api/heatmap')
def get_heatmap_data():
    user_behavior_df = load_csv_data('user_behaviors.csv')

    if not user_behavior_df.empty and 'behavior_time' in user_behavior_df.columns:
        try:
            user_behavior_df['hour'] = pd.to_datetime(user_behavior_df['behavior_time']).dt.hour
            hourly_counts = user_behavior_df.groupby('hour').size().reindex(range(24), fill_value=0)
            max_count = hourly_counts.max() if hourly_counts.max() > 0 else 1
            normalized = (hourly_counts / max_count * 100).astype(int).tolist()
            return jsonify(normalized)
        except:
            pass

    return jsonify(
        [20, 15, 10, 8, 12, 18, 25, 40, 55, 45, 35, 30, 35, 40, 45, 50, 60, 75, 85, 90, 80, 70, 55, 35])


@app.route('/api/payment')
def get_payment_data():
    orders_df = load_csv_data('orders.csv')

    if not orders_df.empty and 'payment_method' in orders_df.columns:
        payment_counts = orders_df['payment_method'].value_counts()
        total = payment_counts.sum()

        if total > 0:
            result = [{'name': str(k), 'value': round((v / total) * 100, 1)} for k, v in payment_counts.items()]
        else:
            result = [
                {'name': '支付宝', 'value': 45},
                {'name': '微信支付', 'value': 35},
                {'name': '花呗', 'value': 12},
                {'name': '银行卡', 'value': 8}
            ]

        return jsonify(result)
    else:
        return jsonify([
            {'name': '支付宝', 'value': 45},
            {'name': '微信支付', 'value': 35},
            {'name': '花呗', 'value': 12},
            {'name': '银行卡', 'value': 8}
        ])


@app.route('/api/rfm')
def get_rfm_data():
    orders_df = load_csv_data('orders.csv')

    if not orders_df.empty and 'user_id' in orders_df.columns and 'order_date' in orders_df.columns and 'actual_payment' in orders_df.columns:
        current_date = datetime.now()
        orders_df['order_date'] = pd.to_datetime(orders_df['order_date'], errors='coerce')
        orders_df = orders_df.dropna(subset=['order_date'])

        if orders_df.empty:
            return jsonify([
                {'name': '重要价值用户', 'value': 25},
                {'name': '重要发展用户', 'value': 20},
                {'name': '重要保持用户', 'value': 18},
                {'name': '重要挽留用户', 'value': 15},
                {'name': '一般价值用户', 'value': 12},
                {'name': '其他', 'value': 10}
            ])

        order_id_col = 'order_id' if 'order_id' in orders_df.columns else 'user_id'
        rfm_data = orders_df.groupby('user_id').agg({
            'order_date': lambda x: (current_date - x.max()).days,
            order_id_col: 'count',
            'actual_payment': 'sum'
        }).reset_index()

        rfm_data.columns = ['user_id', 'recency', 'frequency', 'monetary']

        try:
            rfm_data['R_score'] = pd.qcut(rfm_data['recency'], 4, labels=['R4', 'R3', 'R2', 'R1'], duplicates='drop')
        except:
            rfm_data['R_score'] = 'R1'
        try:
            rfm_data['F_score'] = pd.qcut(rfm_data['frequency'], 4, labels=['F1', 'F2', 'F3', 'F4'], duplicates='drop')
        except:
            rfm_data['F_score'] = 'F1'
        try:
            rfm_data['M_score'] = pd.qcut(rfm_data['monetary'], 4, labels=['M1', 'M2', 'M3', 'M4'], duplicates='drop')
        except:
            rfm_data['M_score'] = 'M1'

        def assign_segment(row):
            if row['R_score'] in ['R1', 'R2'] and row['F_score'] in ['F3', 'F4'] and row['M_score'] in ['M3', 'M4']:
                return '重要价值用户'
            elif row['R_score'] in ['R1', 'R2'] and row['F_score'] in ['F1', 'F2'] and row['M_score'] in ['M3', 'M4']:
                return '重要发展用户'
            elif row['R_score'] in ['R3', 'R4'] and row['F_score'] in ['F3', 'F4'] and row['M_score'] in ['M3', 'M4']:
                return '重要保持用户'
            elif row['R_score'] in ['R3', 'R4'] and row['F_score'] in ['F1', 'F2'] and row['M_score'] in ['M3', 'M4']:
                return '重要挽留用户'
            elif row['R_score'] in ['R1', 'R2'] and row['F_score'] in ['F3', 'F4'] and row['M_score'] in ['M1', 'M2']:
                return '一般价值用户'
            else:
                return '其他'

        rfm_data['segment'] = rfm_data.apply(assign_segment, axis=1)
        segment_counts = rfm_data['segment'].value_counts().to_dict()

        result = []
        for segment, count in segment_counts.items():
            percentage = (count / len(rfm_data)) * 100
            result.append({'name': segment, 'value': round(percentage, 1)})

        return jsonify(result)
    else:
        return jsonify([
            {'name': '重要价值用户', 'value': 25},
            {'name': '重要发展用户', 'value': 20},
            {'name': '重要保持用户', 'value': 18},
            {'name': '重要挽留用户', 'value': 15},
            {'name': '一般价值用户', 'value': 12},
            {'name': '其他', 'value': 10}
        ])


@app.route('/api/orders')
def get_orders_data():
    orders_df = load_csv_data('orders.csv')

    if not orders_df.empty:
        if 'order_date' in orders_df.columns:
            orders_df['order_date'] = pd.to_datetime(orders_df['order_date'])
            recent_orders = orders_df.sort_values('order_date', ascending=False).head(5)
        else:
            recent_orders = orders_df.head(5)

        result = []
        for idx, (_, row) in enumerate(recent_orders.iterrows()):
            user_id = str(row.get('user_id', f"用户***{idx:03d}"))
            user_display = f"用户***{user_id[-3:]}" if len(user_id) > 3 else f"用户***{idx:03d}"

            result.append({
                'id': str(row.get('order_id', f"ORD{idx + 1:03d}")),
                'user': user_display,
                'amount': float(row.get('actual_payment', 0)),
                'status': str(row.get('order_status', '已完成')),
                'time': f"{idx * 3}分钟前"
            })

        return jsonify(result)
    else:
        return jsonify([
            {'id': 'ORD001', 'user': '用户***123', 'amount': 5899, 'status': '已完成', 'time': '2分钟前'},
            {'id': 'ORD002', 'user': '用户***456', 'amount': 1299, 'status': '已付款', 'time': '5分钟前'},
            {'id': 'ORD003', 'user': '用户***789', 'amount': 349, 'status': '已发货', 'time': '8分钟前'},
            {'id': 'ORD004', 'user': '用户***012', 'amount': 8999, 'status': '已完成', 'time': '12分钟前'},
            {'id': 'ORD005', 'user': '用户***345', 'amount': 199, 'status': '已收货', 'time': '15分钟前'}
        ])


@app.route('/api/products')
def get_products_data():
    products_df = load_csv_data('products.csv')

    if not products_df.empty and 'product_name' in products_df.columns:
        if 'sales_count' in products_df.columns and 'price' in products_df.columns:
            products_df['sales_count'] = pd.to_numeric(products_df['sales_count'], errors='coerce').fillna(0)
            products_df['price'] = pd.to_numeric(products_df['price'], errors='coerce').fillna(0)
            products_df['revenue'] = products_df['sales_count'] * products_df['price']
            sort_by = 'revenue'
        elif 'sales_count' in products_df.columns:
            products_df['sales_count'] = pd.to_numeric(products_df['sales_count'], errors='coerce').fillna(0)
            sort_by = 'sales_count'
        else:
            products_df['sales'] = np.random.randint(100, 10000, len(products_df))
            sort_by = 'sales'

        top_products = products_df.sort_values(sort_by, ascending=False).head(5)

        result = []
        for idx, (_, row) in enumerate(top_products.iterrows(), 1):
            product_name = str(row.get('product_name', f"商品{idx}"))

            if 'revenue' in products_df.columns:
                revenue = int(row.get('revenue', 0))
                sales = int(row.get('sales_count', 0))
            elif 'sales_count' in products_df.columns:
                sales = int(row.get('sales_count', 0))
                revenue = sales * 100
            else:
                sales = int(row.get('sales', 0))
                revenue = sales * 100

            result.append({
                'rank': idx,
                'name': product_name[:20] + '...' if len(product_name) > 20 else product_name,
                'sales': sales,
                'revenue': revenue
            })

        return jsonify(result)

    return jsonify([
        {'rank': 1, 'name': 'iPhone 15 Pro Max', 'sales': 2847, 'revenue': 3131700},
        {'rank': 2, 'name': 'MacBook Pro 14', 'sales': 1523, 'revenue': 2284500},
        {'rank': 3, 'name': 'AirPods Pro 2', 'sales': 3245, 'revenue': 649000},
        {'rank': 4, 'name': 'iPad Air 5', 'sales': 1876, 'revenue': 938000},
        {'rank': 5, 'name': 'Apple Watch Series 9', 'sales': 2134, 'revenue': 640200}
    ])


@app.route('/api/analysis')
def get_analysis_data():
    """返回分析报告数据"""
    behaviors = load_csv_data('user_behaviors.csv')
    orders = load_csv_data('orders.csv')
    products = load_csv_data('products.csv')

    # 行为分布
    label_map = {'浏览': '浏览', '点击': '点击', '收藏': '收藏', '加购': '加购'}
    behavior_counts = {}
    total_behaviors = 0
    if not behaviors.empty and 'behavior_type' in behaviors.columns:
        for bt in ['浏览', '点击', '收藏', '加购']:
            c = len(behaviors[behaviors['behavior_type'] == bt])
            behavior_counts[bt] = c
            total_behaviors += c
    else:
        behavior_counts = {'浏览': 14930, '点击': 7665, '收藏': 4456, '加购': 2949}

    order_count = len(orders) if not orders.empty else 15000
    total_gmv = float(orders['actual_payment'].sum()) if not orders.empty and 'actual_payment' in orders.columns else 46165950

    # 活跃时段
    hour_counts = []
    if not behaviors.empty and 'behavior_time' in behaviors.columns:
        try:
            behaviors['hour'] = pd.to_datetime(behaviors['behavior_time']).dt.hour
            hour_counts = behaviors.groupby('hour').size().reindex(range(24), fill_value=0).tolist()
        except:
            hour_counts = [1493, 1150, 766, 745, 588, 445, 370, 396, 520, 670, 820, 960, 1050, 1120, 1060, 990, 1050, 1260, 1480, 1740, 1880, 1790, 1650, 1530]
    else:
        hour_counts = [1493, 1150, 766, 745, 588, 445, 370, 396, 520, 670, 820, 960, 1050, 1120, 1060, 990, 1050, 1260, 1480, 1740, 1880, 1790, 1650, 1530]

    peak_hour = hour_counts.index(max(hour_counts)) if hour_counts else 20

    # 支付方式分布
    payment_data = {}
    if not orders.empty and 'payment_method' in orders.columns:
        pm_counts = orders['payment_method'].value_counts()
        total_pm = pm_counts.sum()
        for pm, c in pm_counts.items():
            payment_data[str(pm)] = round((c / total_pm) * 100, 1)
    else:
        payment_data = {'支付宝': 45, '微信支付': 35, '花呗': 12, '银行卡': 8}

    # 品类分布
    category_data = {}
    if not products.empty and 'category' in products.columns and 'sales_count' in products.columns:
        products['sales_count'] = pd.to_numeric(products['sales_count'], errors='coerce').fillna(0)
        cat_sales = products.groupby('category')['sales_count'].sum().sort_values(ascending=False)
        total_cat_sales = cat_sales.sum()
        for cat, s in cat_sales.items():
            category_data[str(cat)] = round((s / total_cat_sales) * 100, 1)
    else:
        category_data = {'电子产品': 35, '服装鞋帽': 25, '美妆护肤': 15, '家居用品': 12, '食品饮料': 8, '其他': 5}

    # DAU
    dau = len(behaviors['user_id'].unique()) if not behaviors.empty and 'user_id' in behaviors.columns else 4988
    # 客单价
    avg_order_value = round(total_gmv / order_count, 2) if order_count > 0 else 3077.73

    return jsonify({
        'summaryCards': [
            {'num': f'{dau:,}', 'label': '活跃用户 (DAU)', 'color': '#2563eb'},
            {'num': f'{order_count:,}', 'label': '总订单数', 'color': '#16a34a'},
            {'num': f'¥{int(total_gmv):,}', 'label': '总成交额 (GMV)', 'color': '#ea580c'}
        ],
        'behaviorData': {
            'labels': ['浏览', '点击', '收藏', '加购'],
            'values': [behavior_counts.get(b, 0) for b in ['浏览', '点击', '收藏', '加购']]
        },
        'hourData': {
            'labels': [f'{h}:00' for h in range(24)],
            'values': hour_counts
        },
        'insights': [
            {
                'icon': 'd',
                'title': '用户行为分析',
                'stats': [
                    {'label': '浏览行为占比', 'value': f'{round(behavior_counts.get("浏览", 0)/total_behaviors*100, 1)}%', 'cls': 'blue'},
                    {'label': '点击行为占比', 'value': f'{round(behavior_counts.get("点击", 0)/total_behaviors*100, 1)}%'},
                    {'label': '收藏行为占比', 'value': f'{round(behavior_counts.get("收藏", 0)/total_behaviors*100, 1)}%', 'cls': 'orange'},
                    {'label': '加购行为占比', 'value': f'{round(behavior_counts.get("加购", 0)/total_behaviors*100, 1)}%', 'cls': 'green'}
                ],
                'summary': f'在用户行为数据中，浏览行为占比最高为 {round(behavior_counts.get("浏览", 0)/total_behaviors*100, 1)}%，是最主要的用户行为类型。点击行为次之，而收藏和加购行为反映了用户的购买意向，合计占比 {round((behavior_counts.get("收藏", 0)+behavior_counts.get("加购", 0))/total_behaviors*100, 1)}%。'
            },
            {
                'icon': 'e',
                'title': '活跃时段分析',
                'stats': [
                    {'label': '最高峰时段', 'value': f'{peak_hour}:00-{peak_hour+1}:00', 'cls': 'orange'},
                    {'label': '早间高峰', 'value': '10:00-12:00'},
                    {'label': '晚间高峰', 'value': '20:00-22:00'},
                    {'label': '夜间活跃度', 'value': f'{round(hour_counts[22]/max(hour_counts)*100, 1)}%', 'cls': 'purple'}
                ],
                'summary': f'用户最活跃时段为 {peak_hour}:00 前后，晚间 20:00-22:00 为全天流量高峰。建议在高峰时段加大运营投放力度，同时关注早间 10:00-12:00 的用户增长趋势。'
            },
            {
                'icon': 'f',
                'title': '交易与支付分析',
                'stats': [
                    {'label': '总成交额', 'value': f'¥{int(total_gmv):,}', 'cls': 'green'},
                    {'label': '客单价', 'value': f'¥{avg_order_value}', 'cls': 'blue'},
                    {'label': '总订单数', 'value': f'{order_count:,}'},
                    {'label': '主要支付方式', 'value': max(payment_data, key=payment_data.get) if payment_data else '支付宝', 'cls': 'purple'}
                ],
                'summary': f'平台总成交额达 ¥{int(total_gmv):,}，共产生 {order_count:,} 笔订单，客单价为 ¥{avg_order_value}。{max(payment_data, key=payment_data.get) if payment_data else "支付宝"}为主要支付方式，占比 {payment_data.get(max(payment_data, key=payment_data.get), 0)}%。'
            },
            {
                'icon': 'c',
                'title': '品类销售分析',
                'stats': [{'label': k, 'value': f'{v}%', 'cls': 'blue' if i == 0 else ''} for i, (k, v) in enumerate(sorted(category_data.items(), key=lambda x: -x[1])[:5])],
                'summary': f'{"电子产品"}为最畅销品类，占总销售额的 {category_data.get("电子产品", 35)}%。建议优先保障热销品类的供应链稳定，同时通过交叉销售提升其他品类的转化率。'
            }
        ]
    })


if __name__ == '__main__':
    print("  请访问: http://localhost:5000/")
    app.run(debug=True, host='0.0.0.0', port=5000)
