from css import simple_css
import pandas as pd
import streamlit as st
import json
from dokumen_generator import dokumen_generator
import os
from datetime import datetime, timedelta
from google.cloud import storage
from google.oauth2 import service_account
from io import BytesIO, StringIO

def initialize_bucket(credentials_info,bucket_name):
    credentials = service_account.Credentials.from_service_account_info(credentials_info)
    client = storage.Client(credentials=credentials)
    return client.get_bucket(bucket_name)
def load_data_from_gcs(bucket,filename,file_type="csv"):
    blob = bucket.blob(filename)    
    if file_type.lower() == "csv":
        data = blob.download_as_text(encoding='utf-8')
        return pd.read_csv(StringIO(data))
    
    elif file_type.lower() == "excel":
        data = blob.download_as_bytes()
        return pd.read_excel(BytesIO(data))
    
    elif file_type.lower() == "json":
        data = blob.download_as_text(encoding='utf-8')
        return json.loads(data)
    
    else:
        raise ValueError("Unsupported file type. Use 'csv', 'excel', or 'json'.")    
def get_recent_product(cust_no,level,bucket):
    customer_purchases = load_data_from_gcs(bucket,f'customer_purchases_unique_{level.lower()}.json','json')
    cust_produk=customer_purchases[str(cust_no)]
    return cust_produk
def get_current_timestamp_gmt8():
    return (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")

def recommend_product_hierarchy(bucket,cust_no, cluster, level='LEVEL_2'):
    filename = f'rules_{level.lower()}_cluster_v1_{cluster}.xlsx'
    cust_produk=get_recent_product(cust_no,level,bucket)
    blob = bucket.blob(filename)
    if not blob.exists():
        return f"Rules file for cluster {cluster} at {level} not found."
    rules=load_data_from_gcs(bucket,filename,'excel')

    rules['antecedents'] = rules['antecedents'].apply(lambda x: frozenset(eval(x)))
    rules['consequents'] = rules['consequents'].apply(lambda x: frozenset(eval(x)))
    product_metrics = {}
    
    for _, rule in rules.iterrows():
        consequents = list(rule['consequents'])
        for product in consequents:
            if product not in cust_produk:
                if product not in product_metrics:
                    product_metrics[product] = {
                        'confidence': rule['confidence'],
                        'lift': rule['lift'],
                        'support': rule['support']
                    }
                else:
                    product_metrics[product]['confidence'] = max(
                        product_metrics[product]['confidence'],
                        rule['confidence']
                    )
                    product_metrics[product]['lift'] = max(
                        product_metrics[product]['lift'],
                        rule['lift']
                    )
                    product_metrics[product]['support'] = max(
                        product_metrics[product]['support'],
                        rule['support']
                    )


    recommendations = []
    for product, metrics in product_metrics.items():
        recommendations.append({
            'product': product,
            'confidence': f"{metrics['confidence']*100:.2f}%",
            'lift': f"{metrics['lift']:.2f}",
            'support': f"{metrics['support']*100:.2f}%"
        })
    
    recommendations.sort(key=lambda x: float(x['confidence'].strip('%')), reverse=True)


    if recommendations:
        return recommendations
    else:
        return "No Recommendations based on the product bought."
simple_css.add_custom_css()
credentials_info = json.loads(st.secrets["google_cloud"]["credentials"])
st.markdown('<h1 class="main-title"> Customer Segmentation & Product Recommendations Dashboard </h1>', unsafe_allow_html=True)

bucket = initialize_bucket(credentials_info,'dsi-test')
data_customer=load_data_from_gcs(bucket,'results/customer_df_with_clusters_kmeans_without_desc.xlsx','excel')
mapping_cust=load_data_from_gcs(bucket,'mapping_customer_name_customer_no_pendapatan.xlsx','excel')
unique_levels=load_data_from_gcs(bucket,'list_unique_product_levels.json','json')

if 'customer' not in st.session_state:
    st.session_state.customer = None

if 'level_produk' not in st.session_state:
    st.session_state.level_produk = 'LEVEL_2'

if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None

if 'recent_products' not in st.session_state:
    st.session_state.recent_products = None
if 'generate_documents' not in st.session_state:
    st.session_state.generate_documents=None
if 'document_template' not in st.session_state:
    st.session_state.document_template=None
if 'placeholder' not in st.session_state:
    st.session_state.placeholder=None

list_customer=mapping_cust['Cust Name'].loc[mapping_cust['Cust No.'].isin(data_customer['Cust No.'])]
selected_customer = st.selectbox("Customer:", list_customer, index=list_customer.tolist().index(st.session_state.customer) if st.session_state.customer else 0)


if st.session_state.customer != selected_customer:
    st.session_state.customer = selected_customer
    st.session_state.recommendations = None
    st.session_state.recent_products = None
cust_no = mapping_cust['Cust No.'].loc[mapping_cust['Cust Name'] == st.session_state.customer]
cluster = data_customer['cluster_kmeans'].loc[data_customer['Cust No.'] == cust_no.values[0]].values[0]
customer_info = data_customer[data_customer['Cust No.'] == cust_no.values[0]]

st.write("## Customer Information:")
if not customer_info.empty:
    customer_details = customer_info.iloc[0]
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <style>
        .customer-card {
            padding: 20px;
            border-radius: 10px;
            background-color: #f0f7ff;
            color: #003366;
            margin-bottom: 20px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown(f"""
            <div class='customer-card'>
                <h3 style='color: #1f77b; margin-bottom: 10px;'>📋 Basic Info</h3>
                <p style='color: #663301; '><strong>Customer Number:</strong> {customer_details['Cust No.']}</p>
                <p style='color: #663301; '><strong>Total Customer:</strong> {len(data_customer['Cust No.'])}</p>

            </div>
            """, unsafe_allow_html=True)
            
    with col2:
        st.markdown("""
        <style>
        .customer-card {
            padding: 20px;
            border-radius: 20px;
            background-color: #f0f7ff;
            color: #003366;
            margin-bottom: 20px;
        }
        </style>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown(f"""
            <div class='customer-card'>
                <h3 style='color: #1f77b4; margin-bottom: 10px;'>🎯 Segment</h3>
                <p style='color: #663301;'><strong>Cluster:</strong> {customer_info['cluster_kmeans'].values[0] +1}</p>
                <p style='color: #663301;'><strong>Total Cluster Member:</strong> {len(data_customer.loc[data_customer['cluster_kmeans']==customer_info['cluster_kmeans'].values[0]])}</p>
            </div>
            """, unsafe_allow_html=True)
    with st.expander("📊 View Detailed Customer Information Based On Mei - November Transaction Dataset"):
        detailed_info = customer_info.drop(columns=['Cust No.'])
        detailed_info.rename(columns={'freq_transaction':'Transaction Frequency','total_transaction':'Total Transaction Amount','Description':'Customer Type','cluster_kmeans':'Segment Customer'},inplace=True)
        detailed_info['Segment Customer']=detailed_info['Segment Customer']+1
        detailed_info_display = detailed_info.T.reset_index()
        detailed_info_display.columns = ['Metric', 'Value']
        
        st.dataframe(
            detailed_info_display,
            column_config={
                "Metric": "Metrics",
                "Value": st.column_config.NumberColumn(
                    "Value",
                    format="%.2f",
                )
            },
            hide_index=True,
            use_container_width=True
        )
else:
    st.warning("No information found for this customer.")
st.session_state.level_produk = st.selectbox("Level Produk:", ['LEVEL_2'], index=['LEVEL_2'].index(st.session_state.level_produk))
if st.button("Get Recommendations"):
    st.session_state.recommendations = recommend_product_hierarchy(bucket,cust_no.values[0], cluster, st.session_state.level_produk)

if st.session_state.recommendations:
    st.write("### Recommended Products:")
    if isinstance(st.session_state.recommendations, list):
        for rec in st.session_state.recommendations:
            with st.expander(f"🎯 {rec['product']}"):
                st.markdown("**Confidence**")
                st.info(rec['confidence'])
    with st.expander("📝 Fill in Document Details"):
        st.session_state.document_template = st.selectbox("Choose document template: ",['document_penawaran'])
        if(st.session_state.document_template=='document_penawaran'):
            with st.form(key='document_form'):
                no_surat = st.text_input("Nomor Surat", value="testing_1")
                jumlah_lampiran = st.text_input("Jumlah Lampiran", value="testing_1")
                perihal = st.text_input("Document Perihal", value="testing_1")
                alamat = st.text_input("Alamat", value="testing_1")
                timestamp = st.text_input("Timestamp", value=get_current_timestamp_gmt8(), disabled=True)
                if st.session_state.recommendations:
                    product_options = [rec['product'] for rec in st.session_state.recommendations]
                    produk_name = st.selectbox("Choose a Product", product_options)
                else:
                    produk_name = st.text_input("Product", value="testing_1")
                cust_name = st.session_state.customer if st.session_state.customer else "testing_1"

                direktur_utama_name = st.text_input("PIC Name", value="testing_1")
                jabatan = st.text_input("Jabatan", value="testing_1")
                submit_button = st.form_submit_button("Generate Document")
    if submit_button:
        replacements = {
            "no_surat": no_surat,
            "jumlah_lampiran": jumlah_lampiran,
            "perihal": perihal,
            "produk_name": produk_name,
            "cust_name": cust_name,
            "alamat_timestamp": f"{alamat}, {timestamp}",
            "direktur_utama_name": direktur_utama_name,
            "jabatan": jabatan,
        }
        st.session_state.generate_documents = dokumen_generator.create_document(
            'dummy_dokumen_penawaran',
            'testing_dokumen',
            replacements
        )
        with open(st.session_state.generate_documents, "rb") as file:
            st.download_button(
                label="📥 Download Document",
                data=file,
                file_name=f"{os.path.basename(st.session_state.generate_documents)}_{get_current_timestamp_gmt8()}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        st.success("Document successfully generated and ready to download!")


if st.button("Show Recent Product on Mei - November Data"):
    st.session_state.recent_products = get_recent_product(cust_no.values[0], st.session_state.level_produk,bucket)


if st.session_state.recent_products:
    st.write("### Recent Products (Mei - November):")
    if st.session_state.recent_products:
        for product in st.session_state.recent_products:
            st.markdown(
                f"""
                <div style='padding: 3px; border-left: 5px solid #0096c7; background-color: #f8f9fa; margin-bottom: 10px;'>
                    <h4 style='margin: 0; color: #1a1a1a;'>🛍️ {product}</h4>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        with st.expander("📊 Purchase Summary"):
            st.markdown(f"""
            - **Total Products:** {len(st.session_state.recent_products)}
            - **Period:** Mei - November
            - **Status:** Recent Purchases
            """)    

    else:
        st.warning("No recent products found.")