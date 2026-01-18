import React, { useState, useEffect } from 'react';
import { Camera, Film, Loader2, RefreshCw, Play, Image, RotateCw } from 'lucide-react';

const MVDirector = () => {
  const [topic, setTopic] = useState('');
  const [sceneCount, setSceneCount] = useState(8);
  const [aspectRatio, setAspectRatio] = useState('16:9 (Cinema)');
  const [imageProvider, setImageProvider] = useState('Segmind (안정)');
  const [autoGenerate, setAutoGenerate] = useState(true);
  const [maxRetries, setMaxRetries] = useState(3);
  const [executionMode, setExecutionMode] = useState('manual');
  
  const [planData, setPlanData] = useState(null);
  const [turntableImages, setTurntableImages] = useState({});
  const [sceneImages, setSceneImages] = useState({});
  const [imageStatus, setImageStatus] = useState({});
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentStep, setCurrentStep] = useState('');
  const [progress, setProgress] = useState(0);
  const [showPrompts, setShowPrompts] = useState(false);

  const ratioMap = {
    '1:1 (Square)': [1024, 1024],
    '16:9 (Cinema)': [1024, 576],
    '9:16 (Portrait)': [576, 1024],
    '4:3 (Classic)': [1024, 768],
    '3:2 (Photo)': [1024, 683],
    '21:9 (Ultra Wide)': [1024, 439]
  };

  // 턴테이블 이미지 생성 함수
  const generateTurntable = async (character, provider, width, height) => {
    const angles = ['front view', '45 degree view', 'side view', 'back view'];
    const images = {};
    
    for (let i = 0; i < angles.length; i++) {
      const angle = angles[i];
      const prompt = `${character}, ${angle}, turntable reference, character sheet, white background, professional reference, high quality`;
      
      setCurrentStep(`턴테이블 생성 중: ${angle} (${i+1}/${angles.length})`);
      
      try {
        const url = `https://image.pollinations.ai/prompt/${encodeURIComponent(prompt)}?width=${width}&height=${height}&nologo=true&seed=${Math.floor(Math.random() * 999999)}`;
        const response = await fetch(url);
        
        if (response.ok) {
          const blob = await response.blob();
          const imageUrl = URL.createObjectURL(blob);
          images[angle] = imageUrl;
        }
      } catch (error) {
        console.error(`Turntable ${angle} failed:`, error);
      }
      
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    return images;
  };

  // 씬 이미지 생성 함수
  const generateSceneImage = async (prompt, width, height, provider, retries = 3) => {
    const enhancedPrompt = `${prompt}, cinematic, high quality, detailed, professional`;
    
    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        const url = `https://image.pollinations.ai/prompt/${encodeURIComponent(enhancedPrompt)}?width=${width}&height=${height}&nologo=true&seed=${Math.floor(Math.random() * 999999)}`;
        const response = await fetch(url);
        
        if (response.ok) {
          const blob = await response.blob();
          return URL.createObjectURL(blob);
        }
      } catch (error) {
        if (attempt === retries - 1) throw error;
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
    return null;
  };

  // 전체 자동 생성 프로세스
  const handleAutoGenerate = async () => {
    if (!planData) return;
    
    setIsGenerating(true);
    setProgress(0);
    const [width, height] = ratioMap[aspectRatio];
    
    try {
      // 1. 턴테이블 생성
      setCurrentStep('1/2: 캐릭터 턴테이블 생성 중...');
      const turntables = await generateTurntable(
        planData.visual_style.character_prompt,
        imageProvider,
        width,
        height
      );
      setTurntableImages(turntables);
      setProgress(25);
      
      // 2. 씬 이미지 생성
      setCurrentStep('2/2: 씬 이미지 생성 중...');
      const totalScenes = planData.scenes.length;
      const newSceneImages = {};
      const newStatus = {};
      
      for (let i = 0; i < planData.scenes.length; i++) {
        const scene = planData.scenes[i];
        const sceneNum = scene.scene_num;
        
        setCurrentStep(`씬 ${sceneNum} 생성 중... (${i+1}/${totalScenes})`);
        
        const fullPrompt = `${planData.visual_style.character_prompt}, ${scene.image_prompt}`;
        
        try {
          const imageUrl = await generateSceneImage(fullPrompt, width, height, imageProvider, maxRetries);
          
          if (imageUrl) {
            newSceneImages[sceneNum] = imageUrl;
            newStatus[sceneNum] = `✅ 성공 (${imageProvider})`;
          } else {
            newStatus[sceneNum] = '❌ 생성 실패';
          }
        } catch (error) {
          newStatus[sceneNum] = '❌ 생성 실패';
        }
        
        setProgress(25 + ((i + 1) / totalScenes) * 75);
        await new Promise(resolve => setTimeout(resolve, 300));
      }
      
      setSceneImages(newSceneImages);
      setImageStatus(newStatus);
      setCurrentStep('✅ 모든 이미지 생성 완료!');
      
    } catch (error) {
      setCurrentStep('❌ 생성 중 오류 발생');
      console.error(error);
    } finally {
      setIsGenerating(false);
      setProgress(100);
    }
  };

  // 개별 씬 생성
  const handleSingleSceneGenerate = async (sceneNum) => {
    if (!planData) return;
    
    const scene = planData.scenes.find(s => s.scene_num === sceneNum);
    if (!scene) return;
    
    const [width, height] = ratioMap[aspectRatio];
    const fullPrompt = `${planData.visual_style.character_prompt}, ${scene.image_prompt}`;
    
    setImageStatus(prev => ({ ...prev, [sceneNum]: '🎨 생성 중...' }));
    
    try {
      const imageUrl = await generateSceneImage(fullPrompt, width, height, imageProvider, maxRetries);
      
      if (imageUrl) {
        setSceneImages(prev => ({ ...prev, [sceneNum]: imageUrl }));
        setImageStatus(prev => ({ ...prev, [sceneNum]: `✅ 성공 (${imageProvider})` }));
      } else {
        setImageStatus(prev => ({ ...prev, [sceneNum]: '❌ 생성 실패' }));
      }
    } catch (error) {
      setImageStatus(prev => ({ ...prev, [sceneNum]: '❌ 생성 실패' }));
    }
  };

  // 턴테이블 재생성
  const handleTurntableRegenerate = async () => {
    if (!planData) return;
    
    setIsGenerating(true);
    const [width, height] = ratioMap[aspectRatio];
    
    const turntables = await generateTurntable(
      planData.visual_style.character_prompt,
      imageProvider,
      width,
      height
    );
    
    setTurntableImages(turntables);
    setIsGenerating(false);
  };

  // 예시 기획안 로드
  const loadSamplePlan = () => {
    const sample = {
      project_title: "네온 레인: 2050 서울의 밤",
      logline: "비 내리는 사이버펑크 서울에서 진실을 찾는 외로운 형사의 이야기",
      music: {
        style: "신스웨이브, 다크 앰비언트",
        suno_prompt: "Dark synthwave, cyberpunk atmosphere, rain sounds, melancholic melody"
      },
      visual_style: {
        description: "네온사인이 빛나는 어두운 도시, 비 오는 밤의 반사광",
        character_prompt: "Asian male detective, 40s, wearing black trench coat, cyberpunk style, noir atmosphere"
      },
      scenes: [
        {
          scene_num: 1,
          timecode: "00:00-00:05",
          action: "비 내리는 밤, 네온사인이 물웅덩이에 반사되는 서울 거리",
          camera: "Wide shot, 하이앵글",
          image_prompt: "rainy cyberpunk Seoul street at night, neon reflections in puddles, wide aerial view, cinematic",
          video_prompt: "Slow camera descent from high angle, rain falling, neon lights flickering"
        },
        {
          scene_num: 2,
          timecode: "00:05-00:10",
          action: "형사가 우산 없이 비를 맞으며 걷는다",
          camera: "Medium shot, 트래킹샷",
          image_prompt: "detective walking in rain without umbrella, neon lights background, side tracking shot",
          video_prompt: "Smooth tracking shot following character, rain particles visible, atmospheric"
        },
        {
          scene_num: 3,
          timecode: "00:10-00:15",
          action: "홀로그램 광고판들이 빠르게 지나간다",
          camera: "POV shot",
          image_prompt: "holographic advertisements in cyberpunk city, POV perspective, motion blur, vibrant colors",
          video_prompt: "Fast-moving POV through neon advertisements, dynamic camera movement"
        },
        {
          scene_num: 4,
          timecode: "00:15-00:20",
          action: "형사가 작은 술집 앞에 멈춰 선다",
          camera: "Close-up",
          image_prompt: "detective close-up face, rain drops on face, neon sign reflection in eyes, dramatic lighting",
          video_prompt: "Slow zoom into character's face, rain visible, emotional moment"
        }
      ]
    };
    
    setPlanData(sample);
    
    if (autoGenerate) {
      setTimeout(() => handleAutoGenerate(), 500);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white p-4">
      <div className="max-w-7xl mx-auto">
        {/* 헤더 */}
        <div className="text-center mb-8">
          <h1 className="text-5xl font-bold mb-2 bg-gradient-to-r from-purple-400 to-pink-600 bg-clip-text text-transparent">
            🎬 AI MV Director
          </h1>
          <p className="text-gray-400">턴테이블 & 자동 생성 시스템</p>
        </div>

        {/* 설정 패널 */}
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 mb-6 border border-white/20">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-sm mb-2">이미지 비율</label>
              <select 
                value={aspectRatio}
                onChange={(e) => setAspectRatio(e.target.value)}
                className="w-full bg-white/5 border border-white/20 rounded-lg px-3 py-2"
              >
                {Object.keys(ratioMap).map(ratio => (
                  <option key={ratio} value={ratio}>{ratio}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm mb-2">이미지 생성 엔진</label>
              <select 
                value={imageProvider}
                onChange={(e) => setImageProvider(e.target.value)}
                className="w-full bg-white/5 border border-white/20 rounded-lg px-3 py-2"
              >
                <option>Segmind (안정)</option>
                <option>Pollinations Turbo (초고속) ⚡</option>
                <option>Pollinations Flux (고품질)</option>
                <option>Hugging Face Schnell (빠름)</option>
                <option>Image.AI (무제한)</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm mb-2">재시도 횟수</label>
              <input 
                type="number"
                min="1"
                max="5"
                value={maxRetries}
                onChange={(e) => setMaxRetries(parseInt(e.target.value))}
                className="w-full bg-white/5 border border-white/20 rounded-lg px-3 py-2"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input 
                type="checkbox"
                checked={autoGenerate}
                onChange={(e) => setAutoGenerate(e.target.checked)}
                className="w-5 h-5"
              />
              <span>프로젝트 생성 시 자동 이미지 생성</span>
            </label>
          </div>
        </div>

        {/* 데모 버튼 */}
        <div className="text-center mb-6">
          <button
            onClick={loadSamplePlan}
            disabled={isGenerating}
            className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 disabled:from-gray-500 disabled:to-gray-600 px-8 py-3 rounded-xl font-bold text-lg transition-all transform hover:scale-105"
          >
            <Film className="inline-block w-5 h-5 mr-2" />
            예시 프로젝트 로드
          </button>
        </div>

        {/* 진행 상황 */}
        {isGenerating && (
          <div className="bg-blue-500/20 border border-blue-500/50 rounded-xl p-4 mb-6">
            <div className="flex items-center gap-3 mb-3">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="font-semibold">{currentStep}</span>
            </div>
            <div className="w-full bg-white/10 rounded-full h-3 overflow-hidden">
              <div 
                className="bg-gradient-to-r from-blue-500 to-purple-500 h-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* 결과 표시 */}
        {planData && (
          <div className="space-y-6">
            {/* 프로젝트 정보 */}
            <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 border border-white/20">
              <h2 className="text-3xl font-bold mb-2">{planData.project_title}</h2>
              <p className="text-gray-300 mb-4">{planData.logline}</p>
              
              <button
                onClick={() => setShowPrompts(!showPrompts)}
                className="bg-white/10 hover:bg-white/20 px-4 py-2 rounded-lg transition-colors"
              >
                {showPrompts ? '프롬프트 숨기기' : '📋 프롬프트 모두 보기'}
              </button>

              {showPrompts && (
                <div className="mt-4 space-y-2">
                  <div className="bg-black/30 rounded-lg p-3">
                    <div className="text-sm text-gray-400 mb-1">음악 프롬프트</div>
                    <code className="text-xs text-green-300">{planData.music.suno_prompt}</code>
                  </div>
                  <div className="bg-black/30 rounded-lg p-3">
                    <div className="text-sm text-gray-400 mb-1">캐릭터 프롬프트</div>
                    <code className="text-xs text-green-300">{planData.visual_style.character_prompt}</code>
                  </div>
                </div>
              )}
            </div>

            {/* 턴테이블 섹션 */}
            <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 border border-white/20">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-2xl font-bold flex items-center gap-2">
                  <RotateCw className="w-6 h-6" />
                  캐릭터 턴테이블
                </h3>
                <button
                  onClick={handleTurntableRegenerate}
                  disabled={isGenerating}
                  className="bg-purple-500 hover:bg-purple-600 disabled:bg-gray-500 px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  재생성
                </button>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {['front view', '45 degree view', 'side view', 'back view'].map(angle => (
                  <div key={angle} className="bg-black/30 rounded-lg p-3">
                    <div className="text-sm text-gray-400 mb-2 text-center">{angle}</div>
                    {turntableImages[angle] ? (
                      <img 
                        src={turntableImages[angle]} 
                        alt={angle}
                        className="w-full rounded-lg"
                      />
                    ) : (
                      <div className="aspect-square bg-white/5 rounded-lg flex items-center justify-center">
                        <Image className="w-8 h-8 text-gray-600" />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* 씬 이미지 섹션 */}
            <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 border border-white/20">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-2xl font-bold">🎬 스토리보드</h3>
                <button
                  onClick={() => {
                    setSceneImages({});
                    setImageStatus({});
                  }}
                  className="bg-red-500 hover:bg-red-600 px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  모두 초기화
                </button>
              </div>

              <div className="space-y-4">
                {planData.scenes.map((scene) => (
                  <div key={scene.scene_num} className="bg-black/30 rounded-xl p-4 border-l-4 border-purple-500">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h4 className="font-bold text-lg">Scene {scene.scene_num}</h4>
                        <p className="text-sm text-gray-400">{scene.timecode}</p>
                      </div>
                      {sceneImages[scene.scene_num] && (
                        <button
                          onClick={() => {
                            const newImages = { ...sceneImages };
                            delete newImages[scene.scene_num];
                            setSceneImages(newImages);
                          }}
                          className="text-xs bg-white/10 hover:bg-white/20 px-3 py-1 rounded"
                        >
                          🔄 재생성
                        </button>
                      )}
                    </div>

                    {sceneImages[scene.scene_num] ? (
                      <div>
                        <img 
                          src={sceneImages[scene.scene_num]} 
                          alt={`Scene ${scene.scene_num}`}
                          className="w-full rounded-lg mb-2"
                        />
                        <div className="text-xs text-green-400">{imageStatus[scene.scene_num]}</div>
                      </div>
                    ) : (
                      <div>
                        {imageStatus[scene.scene_num] ? (
                          <div className="text-sm text-yellow-400 mb-2">{imageStatus[scene.scene_num]}</div>
                        ) : null}
                        <button
                          onClick={() => handleSingleSceneGenerate(scene.scene_num)}
                          disabled={isGenerating}
                          className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-500 py-2 rounded-lg transition-colors flex items-center justify-center gap-2"
                        >
                          <Camera className="w-4 h-4" />
                          이미지 생성
                        </button>
                      </div>
                    )}

                    <div className="mt-3 text-sm">
                      <p className="text-gray-300"><strong>액션:</strong> {scene.action}</p>
                      <p className="text-gray-300"><strong>카메라:</strong> {scene.camera}</p>
                      
                      {showPrompts && (
                        <div className="mt-2 bg-black/40 rounded p-2">
                          <div className="text-xs text-gray-400 mb-1">이미지 프롬프트:</div>
                          <code className="text-xs text-green-300">
                            {planData.visual_style.character_prompt}, {scene.image_prompt}
                          </code>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MVDirector;
