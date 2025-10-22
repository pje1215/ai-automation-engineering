import React, { useState, useRef } from "react";
import axios from "axios";
import "./App.css";

function App() {
  // API URL 설정 (환경변수 또는 기본값)
  const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8500";

  // 상태 관리
  const [file, setFile] = useState(null);
  const [uploadedData, setUploadedData] = useState(null);
  const [selectedSite, setSelectedSite] = useState("");
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [filteredData, setFilteredData] = useState(null);
  const [stage1Result, setStage1Result] = useState(null);
  const [stage2Result, setStage2Result] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("stage1");
  const fileInputRef = useRef(null);

  // 파일 업로드 핸들러
  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      handleFileUpload(selectedFile);
    }
  };

  // 드래그 앤 드롭 핸들러
  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") {
      setFile(droppedFile);
      handleFileUpload(droppedFile);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  // 파일 업로드 및 데이터 로드
  const handleFileUpload = async (fileToUpload) => {
    const formData = new FormData();
    formData.append("file", fileToUpload);

    try {
      setLoading(true);
      console.log("파일 업로드 시작:", {
        fileName: fileToUpload.name,
        fileSize: fileToUpload.size,
        fileType: fileToUpload.type
      });
      
      const res = await axios.post(`${API_URL}/upload`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      
      console.log("업로드 응답:", res.data);
      setUploadedData(res.data);
      setSelectedSite(res.data.sites[0] || "");
      setSelectedCategories([]);
    } catch (err) {
      console.error("업로드 실패:", err);
      console.error("에러 응답:", err.response?.data);
      
      const errorMessage = err.response?.data?.detail || err.message || "알 수 없는 오류가 발생했습니다.";
      alert(`파일 업로드에 실패했습니다.\n\n에러 내용: ${errorMessage}\n\n자세한 내용은 브라우저 개발자 도구 콘솔을 확인해주세요.`);
    } finally {
      setLoading(false);
    }
  };

  // 카테고리 선택 핸들러
  const handleCategoryToggle = (category) => {
    setSelectedCategories(prev => 
      prev.includes(category) 
        ? prev.filter(cat => cat !== category)
        : [...prev, category]
    );
  };

  // 필터링된 데이터 업데이트
  React.useEffect(() => {
    if (uploadedData && selectedSite && selectedCategories.length > 0) {
      const filtered = uploadedData.data.filter(item => 
        item.site_code === selectedSite && 
        selectedCategories.includes(item.L_category)
      );
      setFilteredData(filtered);
    } else {
      setFilteredData(null);
    }
  }, [uploadedData, selectedSite, selectedCategories]);

  // 1단계 클러스터링 실행
  const handleStage1Clustering = async () => {
    if (!filteredData || filteredData.length === 0) {
      alert("먼저 사이트와 카테고리를 선택해주세요!");
      return;
    }

    try {
      setLoading(true);
      console.log("1단계 클러스터링 요청 데이터:", {
        dataCount: filteredData.length,
        site: selectedSite,
        categories: selectedCategories,
        sampleData: filteredData.slice(0, 2)
      });
      
      const res = await axios.post(`${API_URL}/classify/stage1`, {
        data: filteredData,
        site: selectedSite,
        categories: selectedCategories
      });
      
      console.log("1단계 클러스터링 응답:", res.data);
      setStage1Result(res.data);
      setActiveTab("stage1");
    } catch (err) {
      console.error("1단계 클러스터링 실패:", err);
      console.error("에러 응답:", err.response?.data);
      
      const errorMessage = err.response?.data?.detail || err.message || "알 수 없는 오류가 발생했습니다.";
      alert(`1단계 클러스터링에 실패했습니다.\n\n에러 내용: ${errorMessage}\n\n자세한 내용은 브라우저 개발자 도구 콘솔을 확인해주세요.`);
    } finally {
      setLoading(false);
    }
  };

  // 2단계 세분화 실행
  const handleStage2Segmentation = async () => {
    if (!stage1Result) {
      alert("먼저 1단계 클러스터링을 실행해주세요!");
      return;
    }

    try {
      setLoading(true);
      console.log("2단계 세분화 요청 데이터:", {
        stage1DataCount: stage1Result.data.length,
        sampleData: stage1Result.data.slice(0, 2)
      });
      
      const res = await axios.post(`${API_URL}/classify/stage2`, {
        stage1Data: stage1Result.data
      });
      
      console.log("2단계 세분화 응답:", res.data);
      setStage2Result(res.data);
      setActiveTab("stage2");
    } catch (err) {
      console.error("2단계 세분화 실패:", err);
      console.error("에러 응답:", err.response?.data);
      
      const errorMessage = err.response?.data?.detail || err.message || "알 수 없는 오류가 발생했습니다.";
      alert(`2단계 세분화에 실패했습니다.\n\n에러 내용: ${errorMessage}\n\n자세한 내용은 브라우저 개발자 도구 콘솔을 확인해주세요.`);
    } finally {
      setLoading(false);
    }
  };

  // 결과 다운로드
  const handleDownload = (stage, format = "csv") => {
    const data = stage === "stage1" ? stage1Result : stage2Result;
    if (!data) return;

    const csvContent = convertToCSV(data.data);
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `cluster_${stage}_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // CSV 변환 함수
  const convertToCSV = (data) => {
    if (!data || data.length === 0) return "";
    
    const headers = Object.keys(data[0]);
    const csvContent = [
      headers.join(","),
      ...data.map(row => headers.map(header => `"${row[header] || ""}"`).join(","))
    ].join("\n");
    
    return "\uFEFF" + csvContent; // UTF-8 BOM 추가
  };

  // 1단계 결과 그룹화 (L_category > 대표_lv1명)
  const groupStage1Results = () => {
    if (!stage1Result?.data) return null;

    const grouped = {};
    stage1Result.data.forEach(item => {
      const category = item.L_category;
      const rep = item.대표_lv1명;
      
      if (!grouped[category]) grouped[category] = {};
      if (!grouped[category][rep]) grouped[category][rep] = [];
      
      grouped[category][rep].push(item);
    });

    return grouped;
  };

  // 2단계 결과 그룹화 (L_category > 대표_lv1명 > cluster_lv2)
  const groupStage2Results = () => {
    if (!stage2Result?.data) return null;

    const grouped = {};
    stage2Result.data.forEach(item => {
      const category = item.L_category;
      const rep = item.대표_lv1명;
      const lv2 = item.cluster_lv2;
      
      if (!grouped[category]) grouped[category] = {};
      if (!grouped[category][rep]) grouped[category][rep] = {};
      if (!grouped[category][rep][lv2]) grouped[category][rep][lv2] = [];
      
      grouped[category][rep][lv2].push(item);
    });

    return grouped;
  };

  return (
    <div className="app">
      {/* 헤더 */}
      <div className="header">
        <h1>🧩 상품명 자동 분류 시스템</h1>
        <p>시원스쿨 내부용 | front/back embedding 기반 상품명 자동군집</p>
      </div>

      {/* 파일 업로드 섹션 */}
      <div className="section">
        <h2>상품명 데이터 엑셀 파일을 업로드하세요</h2>
        <div 
          className="upload-area"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onClick={() => fileInputRef.current?.click()}
        >
          <div className="upload-content">
            <div className="upload-icon">☁️</div>
            <p>Drag and drop file here</p>
            <p className="upload-limit">Limit 200MB per file + XLSX</p>
          </div>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx"
          onChange={handleFileChange}
          style={{ display: "none" }}
        />
        
        {file && (
          <div className="file-info">
            <div className="success-banner">
              ✅ {uploadedData?.count || 0}개의 행이 업로드되었습니다.
            </div>
            <p>📁 {file.name} ({Math.round(file.size / 1024)}KB)</p>
          </div>
        )}
      </div>

      {/* 데이터 선택 섹션 */}
      {uploadedData && (
        <div className="section">
          <div className="data-selection">
            <div className="selection-group">
              <label>사이트 선택</label>
              <select 
                value={selectedSite} 
                onChange={(e) => setSelectedSite(e.target.value)}
                className="select-input"
              >
                {uploadedData.sites.map(site => (
                  <option key={site} value={site}>{site}</option>
                ))}
              </select>
            </div>
            
            <div className="selection-group">
              <label>L_category 선택</label>
              <div className="category-tags">
                {uploadedData.categories.map(category => (
                  <span
                    key={category}
                    className={`category-tag ${selectedCategories.includes(category) ? 'selected' : ''}`}
                    onClick={() => handleCategoryToggle(category)}
                  >
                    {category}
                    {selectedCategories.includes(category) && <span className="remove-icon">×</span>}
                  </span>
                ))}
              </div>
            </div>
            
            <div className="selected-count">
              선택된 데이터: {filteredData?.length || 0}개
            </div>
          </div>
        </div>
      )}

      {/* 클러스터링 실행 섹션 */}
      <div className="section">
        <h3>📊 클러스터링 실행</h3>
        <div className="clustering-buttons">
          <div className="stage-card">
            <div className="stage-header">
              <h4>1단계 클러스터링</h4>
              {stage1Result && <span className="completed-badge">✓ 완료</span>}
            </div>
            <p className="stage-description">대표 상품명 기준으로 상품을 그룹화합니다.</p>
            <button 
              className={`cluster-button ${stage1Result ? 'completed' : ''}`}
              onClick={handleStage1Clustering}
              disabled={loading || !filteredData || filteredData.length === 0}
            >
              {loading && !stage2Result ? "처리 중..." : stage1Result ? "1단계 재실행" : "1단계 클러스터링 실행"}
            </button>
          </div>
          
          <div className="stage-card">
            <div className="stage-header">
              <h4>2단계 세분화 (선택)</h4>
              {stage2Result && <span className="completed-badge">✓ 완료</span>}
            </div>
            <p className="stage-description">1단계 결과를 더욱 세밀하게 분류합니다.</p>
            <button 
              className={`cluster-button secondary ${stage2Result ? 'completed' : ''}`}
              onClick={handleStage2Segmentation}
              disabled={loading || !stage1Result}
            >
              {loading && stage1Result ? "처리 중..." : stage2Result ? "2단계 재실행" : "2단계 세분화 실행"}
            </button>
          </div>
        </div>
      </div>

      {/* 결과 다운로드 섹션 */}
      <div className="section">
        <hr />
        <div className="download-section">
          <h3>📂 결과 다운로드</h3>
          <div className="tabs">
            <button 
              className={`tab ${activeTab === "stage1" ? "active" : ""}`}
              onClick={() => setActiveTab("stage1")}
            >
              1단계 결과
            </button>
            <button 
              className={`tab ${activeTab === "stage2" ? "active" : ""}`}
              onClick={() => setActiveTab("stage2")}
            >
              2단계 결과
            </button>
          </div>
          
          <div className="tab-content">
            {activeTab === "stage1" ? (
              <div>
                <h4>🧩 1단계 결과 다운로드</h4>
                <p>1단계: 대표_lv1 기준으로 묶인 상품명 자동 분류 결과입니다.</p>
                {stage1Result ? (
                  <div className="download-buttons">
                    <button 
                      className="download-button"
                      onClick={() => handleDownload("stage1")}
                    >
                      📊 씽킹 데이터 엔진 대입용 엑셀 다운로드
                    </button>
                    <button 
                      className="download-button"
                      onClick={() => handleDownload("stage1")}
                    >
                      💾 현재 기준 저장용 엑셀 다운로드
                    </button>
                  </div>
                ) : (
                  <div className="warning-banner">
                    ⚠️ 먼저 1단계 클러스터링을 실행해주세요.
                  </div>
                )}
              </div>
            ) : (
              <div>
                <h4>🔍 2단계 세분화 결과 다운로드</h4>
                <p>2단계: 대표_lv1 내부에서 세분화된 상품명 자동 분류 결과입니다.</p>
                {stage2Result ? (
                  <div className="download-buttons">
                    <button 
                      className="download-button"
                      onClick={() => handleDownload("stage2")}
                    >
                      📊 씽킹 데이터 엔진 대입용 엑셀 다운로드
                    </button>
                    <button 
                      className="download-button"
                      onClick={() => handleDownload("stage2")}
                    >
                      💾 현재 기준 저장용 엑셀 다운로드
                    </button>
                  </div>
                ) : (
                  <div className="warning-banner">
                    ⚠️ 먼저 2단계 세분화를 실행해주세요.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 클러스터링 결과 표시 */}
      {(stage1Result || stage2Result) && (
        <div className="section">
          <h3>📊 클러스터링 결과</h3>
          
          {/* 결과 탭 네비게이션 */}
          <div className="result-tabs">
            <button 
              className={`result-tab ${activeTab === "stage1" ? "active" : ""}`}
              onClick={() => setActiveTab("stage1")}
              disabled={!stage1Result}
            >
              <span className="tab-icon">📊</span>
              <span className="tab-text">1단계 결과</span>
              {stage1Result && <span className="tab-badge">{stage1Result.count}개</span>}
            </button>
            <button 
              className={`result-tab ${activeTab === "stage2" ? "active" : ""}`}
              onClick={() => setActiveTab("stage2")}
              disabled={!stage2Result}
            >
              <span className="tab-icon">🔍</span>
              <span className="tab-text">2단계 결과</span>
              {stage2Result && <span className="tab-badge">{stage2Result.count}개</span>}
            </button>
          </div>

          {/* 결과 내용 */}
          <div className="result-content">
            {activeTab === "stage1" && stage1Result && (
              <div className="clustering-results">
                {Object.entries(groupStage1Results() || {}).map(([category, representatives]) => (
                  <div key={category} className="category-group">
                    <div className="category-header">
                      <h4>📁 {category}</h4>
                      <span className="count-badge">{Object.keys(representatives).length}개 그룹</span>
                    </div>
                    
                    {Object.entries(representatives).map(([repName, items]) => (
                      <div key={repName} className="cluster-group">
                        <div className="cluster-header">
                          <span className="cluster-title">🔹 {repName}</span>
                          <span className="item-count">{items.length}개 상품</span>
                        </div>
                        <div className="items-list">
                          {items.slice(0, 10).map((item, idx) => (
                            <div key={idx} className="product-item">
                              • {item.pname}
                            </div>
                          ))}
                          {items.length > 10 && (
                            <div className="more-items">
                              ... 외 {items.length - 10}개 상품
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}

            {activeTab === "stage2" && stage2Result && (
              <div className="clustering-results">
                {Object.entries(groupStage2Results() || {}).map(([category, representatives]) => (
                  <div key={category} className="category-group">
                    <div className="category-header">
                      <h4>📁 {category}</h4>
                      <span className="count-badge">{Object.keys(representatives).length}개 그룹</span>
                    </div>
                    
                    {Object.entries(representatives).map(([repName, lv2Clusters]) => (
                      <div key={repName} className="lv1-group">
                        <div className="lv1-header">
                          <span className="lv1-title">▶ {repName}</span>
                          <span className="subcluster-count">{Object.keys(lv2Clusters).length}개 세부 그룹</span>
                        </div>
                        
                        {Object.entries(lv2Clusters).map(([lv2, items]) => (
                          <div key={lv2} className="cluster-group lv2">
                            <div className="cluster-header">
                              <span className="cluster-title">🔸 세부그룹 {lv2}</span>
                              <span className="item-count">{items.length}개 상품</span>
                            </div>
                            <div className="items-list">
                              {items.slice(0, 10).map((item, idx) => (
                                <div key={idx} className="product-item">
                                  • {item.pname}
                                </div>
                              ))}
                              {items.length > 10 && (
                                <div className="more-items">
                                  ... 외 {items.length - 10}개 상품
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
